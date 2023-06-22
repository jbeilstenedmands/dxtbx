from __future__ import annotations

import h5py
import nxmx

from dxtbx.format.FormatNXmxDLS import FormatNXmxDLS
from dxtbx.model.detector_helpers import (
    set_detector_distance,
    set_fast_slow_beam_centre_mm,
)

# some sensible defaults
TRUSTED = (-5, 1e6)
DISTANCE = 116.3
FAST_SLOW_BEAM_CENTRE = 558, 955


class FormatNXmxJF1M(FormatNXmxDLS):
    @staticmethod
    def understand(image_file):
        with h5py.File(image_file) as handle:
            name = nxmx.h5str(FormatNXmxDLS.get_instrument_name(handle))
            file_handle = h5py.File(image_file, swmr=False)
            nxmx_obj = nxmx.NXmx(file_handle)
            nxdata = nxmx_obj.entries[0].data[0]
            if nxdata.signal:
                data = nxdata[nxdata.signal]
            else:
                data = list(nxdata.values())[0]
            image_size = data.shape[1:]
            if image_size == (1066, 1030):
                if name and any(
                    i in name.lower() for i in ["i03", "i04", "i24", "vmxi"]
                ):
                    return True
        return False

    def _start(self):
        super()._start()

        t0 = 0.320
        material = "Si"

        for panel in self._detector_model:
            panel.set_trusted_range((TRUSTED[0], TRUSTED[1]))
            panel.set_thickness(t0)
            panel.set_material(material)
        set_detector_distance(self._detector_model, DISTANCE)
        px_size_f, px_size_s = self._detector_model[0].get_pixel_size()
        fast_slow_beam_centre_mm = (
            FAST_SLOW_BEAM_CENTRE[0] * px_size_f,
            FAST_SLOW_BEAM_CENTRE[1] * px_size_s,
        )
        beam = self._beam()
        assert beam is not None
        set_fast_slow_beam_centre_mm(
            self._detector_model, beam, fast_slow_beam_centre_mm, panel_id=0
        )
