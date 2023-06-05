from __future__ import annotations

from scitbx.array_family import flex

from dxtbx.format.FormatNXMX import FormatNXmx

# NOTE This is a hack for xia2.ssx to work on Swissfel NXmx converted jungfrau data.


class FormatNXmxStillsWithScan(FormatNXmx):
    """Read NXmx-flavour NeXus-format HDF5 data from PSI, cgiving stills a scan."""

    def __init__(self, image_file, **kwargs):
        """Initialise the image structure from the given file."""
        super().__init__(image_file, **kwargs)

    def _start(self):
        super()._start()
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
        self._goniometer_instance = self._goniometer_factory.known_axis((0, 1, 0))

    def _scan(self):
        return self._scan_model

    def get_scan(self, index=None):
        if index is None:
            return self._scan()
        scan = self._scan()
        if scan is not None:
            return scan[index]
        return scan

    def get_goniometer(self, index=None):
        return self._goniometer_instance
