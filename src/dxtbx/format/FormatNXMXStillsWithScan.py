from __future__ import annotations

import h5py

from scitbx.array_family import flex

import dxtbx.model
import dxtbx.nexus
from dxtbx.format.FormatNXmx import (
    FormatNXmx,
    detector_between_sample_and_source,
    inverted_distance_detector,
)

# NOTE This is a hack for xia2.ssx to work on Swissfel NXmx converted jungfrau data.


class FormatNXmxStillsWithScan(FormatNXmx):
    """Read NXmx-flavour NeXus-format HDF5 data from PSI, cgiving stills a scan."""

    _detector_model = None

    def __init__(self, image_file, **kwargs):
        """Initialise the image structure from the given file."""
        super().__init__(image_file, **kwargs)

    def _start(self):
        self._static_mask = None

        self._cached_file_handle = h5py.File(self._image_file, swmr=True)
        nxmx_obj = self._get_nxmx(self._cached_file_handle)
        nxentry = nxmx_obj.entries[0]
        nxsample = nxentry.samples[0]
        nxinstrument = nxentry.instruments[0]
        nxdetector = nxinstrument.detectors[0]
        nxbeam = nxinstrument.beams[0]
        # self._goniometer_model = dxtbx.nexus.get_dxtbx_goniometer(nxsample)
        self._beam_factory = dxtbx.nexus.CachedWavelengthBeamFactory(nxbeam)
        wavelength = self._beam_factory.make_beam(index=0).get_wavelength()
        if not FormatNXmxStillsWithScan._detector_model:
            FormatNXmxStillsWithScan._detector_model = dxtbx.nexus.get_dxtbx_detector(
                nxdetector, wavelength
            )
        self._detector_model = FormatNXmxStillsWithScan._detector_model
        # if the detector is between the sample and the source, and perpendicular
        # to the beam, then invert the distance vector, as this is probably wrong
        beam = self._beam()
        if detector_between_sample_and_source(self._detector_model, beam):
            self._detector_model = inverted_distance_detector(self._detector_model)

        self._scan_model = dxtbx.nexus.get_dxtbx_scan(nxsample, nxdetector)
        self._static_mask = dxtbx.nexus.get_static_mask(nxdetector)
        self._bit_depth_readout = nxdetector.bit_depth_readout

        if self._scan_model:
            self._num_images = len(self._scan_model)
        else:
            nxdata = nxmx_obj.entries[0].data[0]
            if nxdata.signal:
                data = nxdata[nxdata.signal]
            else:
                data = list(nxdata.values())[0]
            self._num_images, *_ = data.shape
        self._setup_gonio_and_scan()

    def _setup_gonio_and_scan(self):
        from dxtbx.model.scan import Scan

        num_images = self.get_num_images()
        image_range = (1, num_images)
        oscillation = (0.0, 0)

        exposure_time = flex.double(num_images, 0)
        epochs = flex.double(num_images, 0)

        # Construct the model
        self._scan_model = Scan(image_range, oscillation, exposure_time, epochs)
        self._goniometer_model = dxtbx.model.GoniometerFactory.make_goniometer(
            (0, 1, 0), (1, 0, 0, 0, 1, 0, 0, 0, 1)
        )
