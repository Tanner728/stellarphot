import numpy as np
import pytest

from astropy.table import QTable
from astropy.stats import gaussian_sigma_to_fwhm
from astropy import units as u

from stellarphot.photometry import (source_detection, compute_fwhm)

from fake_image import FakeImage

@pytest.mark.parametrize('units', [u.pixel, None])
def test_compute_fwhm(units):
    fake_image = FakeImage()
    sources = fake_image.sources
    if units is not None:
        # It turns out having a unit on a column is not the same as
        # things in the column having units. The construct below ensures
        # that the source table values have units.
        # Do not try: sources['x_mean'] = sources['x_mean'] * units
        # Turns out individual values do NOT have units in that case.
        sources['x_mean'] = [v * units for v in sources['x_mean']]
        sources['y_mean'] = [v * units for v in sources['y_mean']]

    fwhm_x, fwhm_y = compute_fwhm(fake_image.image, sources,
                                  x_column='x_mean', y_column='y_mean')


def test_detect_source_number_location():
    """
    Make sure we detect the sources in the input table....
    """
    fake_image = FakeImage()
    sources = QTable(fake_image.sources, units={'x_mean':u.pixel, 'y_mean':u.pixel,
                                                'x_stddev':u.pixel, 'y_stddev':u.pixel})
    # print(sources)
    # Pass only one value for the sky background for source detection
    sky_per_pix = sources['sky_per_pix_avg'].mean()
    found_sources = source_detection(fake_image.image,
                                     fwhm=2 * sources['x_stddev'].mean(),
                                     threshold=10,
                                     sky_per_pix_avg=sky_per_pix)
    # Sort by flux so we can reliably match them
    sources.sort('amplitude')
    found_sources.sort('flux')

    # Do we have the right number of sources?
    assert len(sources) == len(found_sources)

    for inp, out in zip(sources, found_sources):
        # Do the positions match?
        np.testing.assert_allclose(out['xcenter'], inp['x_mean'],
                                   rtol=1e-5, atol=0.05)
        np.testing.assert_allclose(out['ycenter'], inp['y_mean'],
                                   rtol=1e-5, atol=0.05)
        np.testing.assert_allclose(gaussian_sigma_to_fwhm * (inp['x_stddev']
                                                             + inp['y_stddev']) / 2,
                                   out['width'],
                                   rtol=1e-5, atol=0.05)


def test_detect_source_with_padding():
    """
    Make sure we detect the sources in the input table....
    """
    fake_image = FakeImage()
    sources = QTable(fake_image.sources, units={'x_mean':u.pixel, 'y_mean':u.pixel,
                                                'x_stddev':u.pixel, 'y_stddev':u.pixel})
    # Pass only one value for the sky background for source detection
    sky_per_pix = sources['sky_per_pix_avg'].mean()
    # Padding was chosen to be large enough to ensure that one of the sources in
    # test_sources.csv would land too close to the edge of the image.
    found_sources = source_detection(fake_image.image,
                                     fwhm=2 * sources['x_stddev'].mean(),
                                     threshold=10,
                                     sky_per_pix_avg=sky_per_pix, padding=95)

    # Did we drop one source because it was too close to the edge?
    assert len(sources) - 1 == len(found_sources)