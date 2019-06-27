#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# An implementation of the SMV image reader for ADSC images. Inherits from
# FormatSMVADSC, customised for example on ALS beamline 8.2.1 from back in the
# day which had it's own way of recording beam centre.

from __future__ import absolute_import, division, print_function

from dxtbx.format.FormatSMVADSCSN import FormatSMVADSCSN


class FormatSMVADSCSN445(FormatSMVADSCSN):
    """A class for reading SMV format ADSC images, and correctly constructing
    a model for the experiment from this, for instrument number 445."""

    @staticmethod
    def understand(image_file):
        """Check to see if this is ADSC SN 445."""

        # check this is detector serial number 445

        size, header = FormatSMVADSCSN.get_smv_header(image_file)

        return int(header["DETECTOR_SN"]) == 445

    def __init__(self, image_file, **kwargs):
        """Initialise the image structure from the given file, including a
        proper model of the experiment."""

        from dxtbx import IncorrectFormatError

        if not self.understand(image_file):
            raise IncorrectFormatError(self, image_file)

        FormatSMVADSCSN.__init__(self, image_file, **kwargs)

    def _detector(self):
        """Return a model for a simple detector, presuming no one has
        one of these on a two-theta stage. Assert that the beam centre is
        provided in the Mosflm coordinate frame."""

        distance = float(self._header_dictionary["DISTANCE"])
        beam_x = float(self._header_dictionary["DENZO_XBEAM"])
        beam_y = float(self._header_dictionary["DENZO_YBEAM"])
        pixel_size = float(self._header_dictionary["PIXEL_SIZE"])
        image_size = (
            float(self._header_dictionary["SIZE1"]),
            float(self._header_dictionary["SIZE2"]),
        )
        trusted_range = self._adsc_trusted_range(pedestal=40)

        return self._detector_factory.simple(
            "CCD",
            distance,
            (beam_y, beam_x),
            "+x",
            "-y",
            (pixel_size, pixel_size),
            image_size,
            trusted_range,
            [],
            gain=self._adsc_module_gain(),
        )

    def get_raw_data(self):
        """Get the pixel intensities (i.e. read the image and return as a
        flex array of integers.)"""

        from boost.python import streambuf
        from dxtbx.ext import read_uint16, read_uint16_bs, is_big_endian
        from scitbx.array_family import flex

        assert len(self.get_detector()) == 1
        image_pedestal = 40
        panel = self.get_detector()[0]
        size = panel.get_image_size()
        if self._header_dictionary["BYTE_ORDER"] == "big_endian":
            big_endian = True
        else:
            big_endian = False

        with FormatSMVADSCSN.open_file(self._image_file, "rb") as fh:
            fh.seek(self._header_size)

            if big_endian == is_big_endian():
                raw_data = read_uint16(streambuf(fh), int(size[0] * size[1]))
            else:
                raw_data = read_uint16_bs(streambuf(fh), int(size[0] * size[1]))

        # apply image pedestal, will result in *negative pixel values*

        raw_data -= image_pedestal

        image_size = panel.get_image_size()
        raw_data.reshape(flex.grid(image_size[1], image_size[0]))

        return raw_data
