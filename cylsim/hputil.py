"""Convenience functions for dealing with Healpix maps.

Uses the healpy module.
"""

import healpy

import numpy as np


def ang_positions(nside):
    """Fetch the angular position of each pixel in a map.

    Parameters
    ----------
    nside : scalar
        The size of the map (nside is a definition specific to Healpix).

    Returns
    -------
    angpos : np.ndarray
        The angular position (in spherical polars), of each pixel in a
        Healpix map. Packed at [ [theta1, phi1], [theta2, phi2], ...]
    """
    npix = healpy.nside2npix(int(nside))
    
    angpos = np.empty([npix, 2], dtype = np.float64)

    angpos[:, 0], angpos[:, 1] = healpy.pix2ang(nside, np.arange(npix))

    return angpos


def nside_for_lmax(lmax, accuracy_boost=1):
    """Return an nside appropriate for a spherical harmonic decomposition.

    Parameters
    ----------
    lmax : integer
        Maximum multipole in decomposition.

    Returns
    -------
    nside : integer
        Appropriate nside for decomposition. Is power of two.
    """
    nside = int(2**(accuracy_boost + np.ceil(np.log((lmax + 1) / 3.0) / np.log(2.0))))
    return nside


def unpack_alm(alm, lmax, fullm = False):
    """Unpack :math:`a_{lm}` from Healpix format into 2D [l,m] array.

    This only unpacks into the
    
    Parameters
    ----------
    alm : np.ndarray
        a_lm packed in Healpix format.
    lmax : integer
        The maximum multipole in the a_lm's.
    fullm : boolean, optional
        Write out the negative m values.

    Returns
    -------
    almarray : np.ndarray
        a_lm in a 2D array packed as [l,m]. If `fullm` write out the negative
        m's, packed into the second half of the array (they can be indexed as
        [l,-m]).
    """
    almarray = np.zeros((lmax+1, lmax+1), dtype=alm.dtype)

    (almarray.T)[np.triu_indices(lmax+1)] = alm

    if fullm:
        almarray = _make_full_alm(almarray)

    return almarray


def pack_alm(almarray, lmax = None):
    """Pack :math:`a_{lm}` into Healpix format from 2D [l,m] array.

    This only unpacks into the
    
    Parameters
    ----------
    almarray : np.ndarray
        a_lm packed in a 2D array as [l,m].
    lmax : integer, optional
        The maximum multipole in the a_lm's. If `None` (default) work it out
        from the first index.

    Returns
    -------
    alm : np.ndarray
        a_lm in Healpix packing. If `fullm` write out the negative
        m's, packed into the second half of the array (they can be indexed as
        [l,-m]).
    """
    if (2*almarray.shape[1] - 1) == almarray.shape[0]:
        almarray = _make_half_alm(almarray)

    if not lmax:
        lmax = almarray.shape[0] - 1

    alm = (almarray.T)[np.triu_indices(lmax+1)]

    return alm



def _make_full_alm(alm_half, centered = False):
    ## Construct an array of a_{lm} including both positive and
    ## negative m, from one including only positive m.
    lmax, mmax = alm_half.shape

    alm = np.zeros([lmax, 2*mmax - 1], dtype=alm_half.dtype)

    alm_neg = alm_half[:, :0:-1].conj()
    mfactor = (-1)**np.arange(mmax)[:0:-1][np.newaxis, :]
    alm_neg = mfactor *alm_neg

    if not centered:
        alm[:lmax, :mmax] = alm_half
        alm[:lmax, mmax:] = alm_neg
    else:
        alm[:lmax, (mmax-1):] = alm_half
        alm[:lmax, :(mmax-1)] = alm_neg

    return alm


def _make_half_alm(alm_full):
    ## Construct an array of a_{lm} including only positive m, from one both
    ## positive and negative m.
    lside, mside = alm_full.shape

    alm = np.zeros([lside, lside], dtype=alm_full.dtype)

    # Copy zero frequency modes
    alm[:,0] = alm_full[:,0]

    # Project such that only alms corresponding to a real field are included.
    for mi in range(1,lside):
        alm[:,mi] = 0.5*(alm_full[:,mi] + (-1)**0.5 * alm_full[:,mi])

    return alm


    

def sphtrans_real(hpmap, lmax = None, lside = None):
    """Spherical Harmonic transform of a real map.

    Parameters
    ----------
    hpmap : np.ndarray
        A Healpix map.
    lmax : scalar, optional
        The maximum l to calculate. If `None` (default), calculate up
        to 3*nside - 1.

    Returns
    -------
    alm : np.ndarray
        A 2d array of alms, packed as alm[l,m].

    Notes
    -----
    This only includes m > 0. As this is the transform of a real field:

    .. math:: a_{l -m} = (-1)^m a_{lm}^*
    """
    if lmax == None:
        lmax = 3*healpy.npix2nside(hpmap.size) - 1

    if lside == None or lside < lmax:
        lside = lmax

    alm = np.zeros([lside+1, lside+1], dtype=np.complex128)

    tlm = healpy.map2alm(np.ascontiguousarray(hpmap), lmax=lmax)

    alm[np.triu_indices(lmax+1)] = tlm

    return alm.T


    
def sphtrans_complex(hpmap, lmax = None, centered = False, lside = None):
    """Spherical harmonic transform of a complex function.

    Parameters
    ----------
    hpmap : np.ndarray
        A complex Healpix map.
    lmax : scalar, optional
        The maximum l to calculate. If `None` (default), calculate up to 3*nside
        - 1.
    centered : boolean, optional
        If False (default) similar to an FFT, alm[l,:lmax+1] contains m >= 0,
        and the latter half alm[l,lmax+1:], contains m < 0. If True the first
        half of alm[l,:] contains m < 0, and the second half m > 0. m = 0 is
        the central column.
        
    Returns
    -------
    alm : np.ndarray
        A 2d array of alms, packed as alm[l,m].
    """
    if lmax == None:
        lmax = 3*healpy.npix2nside(hpmap.size) - 1

    rlm = _make_full_alm(sphtrans_real(hpmap.real, lmax = lmax, lside=lside),
                         centered = centered)
    ilm = _make_full_alm(sphtrans_real(hpmap.imag, lmax = lmax, lside=lside),
                         centered = centered)

    alm = rlm + 1.0J * ilm

    return alm


def sphtrans_real_pol(hpmaps, lmax = None, lside=None):
    """Spherical Harmonic transform of polarisation functions on the sky.

    Accepts real T, Q and U like maps, and returns :math:`a^T_{lm}`
    :math:`a^E_{lm}` and :math:`a^B_{lm}`.

    Parameters
    ----------
    hpmaps : list of np.ndarray
        A list of Healpix maps, assumed to be T, Q, and U.
    lmax : scalar, optional
        The maximum l to calculate. If `None` (default), calculate up to 3*nside
        - 1.

    Returns
    -------
    alm_T, alm_E, alm_B : np.ndarray
        A 2d array of alms, packed as alm[l,m].

    Notes
    -----
    This only includes m > 0. As these are the transforms of a real field:

    .. math:: a_{l -m} = (-1)^m a_{lm}^*
    """
    if lmax == None:
        lmax = 3*healpy.npix2nside(hpmaps[0].size) - 1

    if lside == None or lside < lmax:
        lside = lmax

    alms = [np.zeros([lside+1, lside+1], dtype=np.complex128) for i in range(3)]

    tlms = healpy.map2alm([np.ascontiguousarray(hpmap) for hpmap in hpmaps],
                          lmax=lmax)

    for i in range(3):
        alms[i][np.triu_indices(lmax+1)] = tlms[i]

    return [alm.T for alm in alms]




def sphtrans_complex_pol(hpmaps, lmax = None, centered = False, lside=None):
    """Spherical harmonic transform of the polarisation on the sky (can be
    complex).

    Accepts complex T, Q and U like maps, and returns :math:`a^T_{lm}`
    :math:`a^E_{lm}` and :math:`a^B_{lm}`.
    
    Parameters
    ----------
    hpmaps : np.ndarray
         A list of complex Healpix maps, assumed to be T, Q, and U.
    lmax : scalar, optional
        The maximum l to calculate. If `None` (default), calculate up to 3*nside
        - 1.
    centered : boolean, optional
        If False (default) similar to an FFT, alm[l,:lmax+1] contains m >= 0,
        and the latter half alm[l,lmax+1:], contains m < 0. If True the first
        half opf alm[l,:] contains m < 0, and the second half m > 0. m = 0 is
        the central column.
        
    Returns
    -------
    alm_T, alm_E, alm_B : np.ndarray
        A 2d array of alms, packed as alm[l,m].
    """
    if lmax == None:
        lmax = 3*healpy.npix2nside(hpmaps[0].size) - 1

    rlms = [_make_full_alm(alm, centered = centered) for alm in
            sphtrans_real_pol([hpmap.real for hpmap in hpmaps], lmax = lmax, lside=lside)]
    ilms = [_make_full_alm(alm, centered = centered) for alm in
            sphtrans_real_pol([hpmap.imag for hpmap in hpmaps], lmax = lmax, lside=lside)]

    alms = [rlm + 1.0J * ilm for rlm, ilm in zip(rlms, ilms)]

    return alms
    
