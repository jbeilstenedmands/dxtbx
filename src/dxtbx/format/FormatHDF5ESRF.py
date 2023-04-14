from __future__ import annotations

import os
import sys

import h5py
import numpy as np

from scitbx.array_family import flex

from dxtbx.format.FormatHDF5 import FormatHDF5
from dxtbx.format.FormatStill import FormatStill

# defaults from 2022
# wavelength=1.072528
# distance = 175.22
# beam centre (fast, slow in mm) ~ 78.34, 85.05 (x,y) (in pixels=~1034,1139)
# these correspond to geometry.detector.panel.origin=-78.34,85.05,-175

# note, to set the wavelength, just use geometry.beam.wavelength= in dials.import
# note, to set the distance, just use geometry.detector.distance= in dials.import
# note, to set the distance (z) and beam centre (x,y), just use
# geometry.detector.panel.origin=-x,y,-z  (watch out for the signs!)


class FormatHDF5ESRF(FormatHDF5, FormatStill):

    _cached_first_image = {}
    _cached_n_images = {}

    @staticmethod
    def understand(image_file):
        with h5py.File(image_file, "r") as h5_handle:
            if len(h5_handle) != 1:
                return False
            if "ESRF_HDF5_JF" in os.environ:
                if os.environ["ESRF_HDF5_JF"] == "TRUE":
                    return True
        return False

    def _start(self):
        super()._start()
        image_file = self.get_image_file()
        self._h5_handle = h5py.File(image_file, "r")
        if image_file not in FormatHDF5ESRF._cached_n_images:
            n_images = self._h5_handle["entry_0000"]["measurement"]["data"].shape[0]
            FormatHDF5ESRF._cached_n_images[image_file] = n_images
        if image_file not in FormatHDF5ESRF._cached_first_image:
            FormatHDF5ESRF._cached_first_image[image_file] = (
                self._h5_handle["entry_0000"]["measurement"]["data"][0] / 478.6
            )

    def get_raw_data(self, index=None):
        if index is None:
            index = 0

        data = self._h5_handle["entry_0000"]["measurement"]["data"][index] / 478.6
        return flex.double(data.astype(float))

    def get_num_images(self):
        return FormatHDF5ESRF._cached_n_images[self.get_image_file()]

    def get_beam(self, index=None):
        return self._beam(index)

    def _beam(self, index=None):
        if index is None:
            index = 0
        return self._beam_factory.simple(1.072528)

    def get_detector(self, index=None):
        return self._detector(index)

    def _detector(self, index=None):
        distance = 175.22
        first_image = FormatHDF5ESRF._cached_first_image[self.get_image_file()]
        image_size = first_image.shape
        pixel_size = 0.075
        beam_x = 78.34
        beam_y = 85.05
        trusted_range = (
            -10,  # ????? (needs to be less that zero due to pedestal subtraction)
            1e9,  # ?????
        )
        mask_sel = first_image == 0
        mask = np.zeros(image_size, dtype=int)
        mask[mask_sel] = 1

        return self._detector_factory.simple(
            sensor="UNKNOWN",
            distance=distance,
            beam_centre=(beam_x, beam_y),
            fast_direction="+x",
            slow_direction="-y",
            pixel_size=(pixel_size, pixel_size),
            image_size=(image_size[1], image_size[0]),
            trusted_range=trusted_range,
            mask=mask,
        )

    def _goniometer(self):
        return self._goniometer_factory.known_axis((0, 1, 0))

    def _scan(self):
        return self._scan_factory.make_scan(
            image_range=(1, self._n_images),
            exposure_times=1.0,
            oscillation=(0.0, 0.0),
            epochs=list(range(self._n_images)),
        )


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(FormatHDF5ESRF.understand(arg))
