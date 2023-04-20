from __future__ import annotations

import sys

import h5py

from scitbx.array_family import flex

from dxtbx import flumpy
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


class FormatHDF5ESRFJungfrau4M(FormatHDF5, FormatStill):

    _cached_mask = None

    @staticmethod
    def understand(image_file):
        with h5py.File(image_file, "r") as h5_handle:
            if len(h5_handle) != 1:
                return False
            key = list(h5_handle.keys())[0]
            if "instrument" not in h5_handle[key]:
                return False
            if "jungfrau4m_rr_smx" not in h5_handle[key]["instrument"]:
                return False
        return True

    def _start(self):
        super()._start()
        image_file = self.get_image_file()
        self._h5_handle = h5py.File(image_file, "r")
        self.key = list(self._h5_handle.keys())[0]
        self.n_images = self._h5_handle[self.key]["instrument"]["jungfrau4m_rr_smx"][
            "data"
        ].shape[0]
        self.adus_per_photon = 478.6
        self.image_size = tuple(
            self._h5_handle[self.key]["instrument"]["jungfrau4m_rr_smx"]["data"].shape[
                1:
            ]
        )
        self.wavelength = 1.072528
        self.detector_params = {
            "distance": 175.22,
            "pixel_size": 0.075,
            "beam_x": 78.34,
            "beam_y": 85.05,
        }

    def get_raw_data(self, index=None):
        if index is None:
            index = 0

        data = (
            self._h5_handle[self.key]["measurement"]["data"][index]
            / self.adus_per_photon
        )
        return flex.double(data.astype(float))

    def get_num_images(self):
        return self.n_images

    def get_beam(self, index=None):
        return self._beam(index)

    def _beam(self, index=None):
        if index is None:
            index = 0
        return self._beam_factory.simple(self.wavelength)

    def get_detector(self, index=None):
        return self._detector(index)

    def get_static_mask(self):
        if FormatHDF5ESRFJungfrau4M._cached_mask is None:
            first_image = (
                self._h5_handle[self.key]["measurement"]["data"][0]
                / self.adus_per_photon
            )
            mask_sel = first_image == 0
            mask_sel = flumpy.from_numpy(mask_sel.reshape(-1))
            mask_sel.reshape(flex.grid(self.image_size[0], self.image_size[1]))
            mask = flex.bool(flex.grid(self.image_size[0], self.image_size[1]), True)
            mask.set_selected(mask_sel, False)
            FormatHDF5ESRFJungfrau4M._cached_mask = mask
        return FormatHDF5ESRFJungfrau4M._cached_mask

    def _detector(self, index=None):

        trusted_range = (
            -10,  # ????? (needs to be less that zero due to pedestal subtraction)
            1e9,  # ?????
        )

        return self._detector_factory.simple(
            sensor="UNKNOWN",
            distance=self.detector_params["distance"],
            beam_centre=(
                self.detector_params["beam_x"],
                self.detector_params["beam_y"],
            ),
            fast_direction="+x",
            slow_direction="-y",
            pixel_size=(
                self.detector_params["pixel_size"],
                self.detector_params["pixel_size"],
            ),
            image_size=(self.image_size[1], self.image_size[0]),
            trusted_range=trusted_range,
            mask=self.get_static_mask(),
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
        print(FormatHDF5ESRFJungfrau4M.understand(arg))
