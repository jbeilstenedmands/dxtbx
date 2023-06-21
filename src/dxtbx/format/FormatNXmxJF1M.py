from __future__ import annotations

from dxtbx.format.FormatNXmxDLS import FormatNXmxDLS

trusted = (-5, 1e6)


class FormatNXmxJF1M(FormatNXmxDLS):
    def _start(self):
        super()._start()
        for panel in self._detector_model:
            panel.set_trusted_range((trusted[0], trusted[1]))
            panel.set_image_size((1066, 1030))
