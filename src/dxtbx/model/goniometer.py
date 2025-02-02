from __future__ import annotations

import math

import pycbf

import libtbx.phil
from scitbx.array_family import flex

try:
    from ..dxtbx_model_ext import Goniometer, KappaGoniometer, MultiAxisGoniometer
except ModuleNotFoundError:
    from dxtbx_model_ext import (  # type: ignore
        Goniometer,
        KappaGoniometer,
        MultiAxisGoniometer,
    )

__all__ = [
    "Goniometer",
    "GoniometerFactory",
    "KappaGoniometer",
    "MultiAxisGoniometer",
    "goniometer_phil_scope",
]

goniometer_phil_scope = libtbx.phil.parse(
    """
  goniometer
    .expert_level = 1
    .short_caption = "Goniometer overrides"
  {

    axis = None
      .type = floats(size=3)
      .help = "Override the axis for a single axis goniometer. Equivalent to"
              "providing a single 3D vector to 'axes'."
      .short_caption="Goniometer axis"

    axes = None
      .type = floats
      .help = "Override the goniometer axes. Axes must be provided in the"
              "order crystal-to-goniometer, i.e. for a Kappa goniometer"
              "phi,kappa,omega"
      .short_caption="Goniometer axes"

    angles = None
      .type = floats
      .help = "Override the goniometer angles. Axes must be provided in the"
              "order crystal-to-goniometer, i.e. for a Kappa goniometer"
              "phi,kappa,omega"
      .short_caption = "Goniometer angles"

    names = None
      .type = str
      .help = "The multi axis goniometer axis names"
      .short_caption = "The axis names"

    scan_axis = None
      .type = int
      .help = "The scan axis"
      .short_caption = "The scan axis"

    fixed_rotation = None
      .type = floats(size=9)
      .help = "Override the fixed rotation matrix"
      .short_caption = "Fixed rotation matrix"

    setting_rotation = None
      .type = floats(size=9)
      .help = "Override the setting rotation matrix"
      .short_caption = "Setting rotation matrix"

    invert_rotation_axis = False
      .type = bool
      .help = "Invert the rotation axis"
      .short_caption = "Invert rotation axis"

  }
"""
)


class GoniometerFactory:
    """A factory class for goniometer objects, which will encapsulate
    some standard goniometer designs to make it a little easier to get
    started with all of this - for cases when we are not using a CBF.
    When we have a CBF just use that factory method and everything will be
    peachy."""

    @staticmethod
    def single_axis_goniometer_from_phil(params, reference=None):
        """
        Generate or overwrite a single axis goniometer

        """

        # Check the axis parameter and copy from axes if required
        if params.goniometer.axis is None:
            params.goniometer.axis = params.goniometer.axes
        if params.goniometer.axis is not None and len(params.goniometer.axis) != 3:
            raise RuntimeError("Single axis goniometer requires 3 axis values")

        # Check the angles parameter
        if params.goniometer.angles is not None:
            raise RuntimeError("Single axis goniometer requires angles == None")

        # Check the names parameter
        if params.goniometer.names is not None:
            raise RuntimeError("Single axis goniometer requires names == None")

        # Init the gonionmeter
        if reference is None:
            goniometer = Goniometer()
        else:
            goniometer = reference

        # Set the parameters
        if params.goniometer.axis is not None:
            goniometer.set_rotation_axis_datum(params.goniometer.axis)
        if params.goniometer.fixed_rotation is not None:
            goniometer.set_fixed_rotation(params.goniometer.fixed_rotation)
        if params.goniometer.setting_rotation is not None:
            goniometer.set_setting_rotation(params.goniometer.setting_rotation)
        if params.goniometer.invert_rotation_axis is True:
            rotation_axis = goniometer.get_rotation_axis_datum()
            goniometer.set_rotation_axis_datum([-x for x in rotation_axis])

        return goniometer

    @staticmethod
    def multi_axis_goniometer_from_phil(params, reference=None):
        # Check the axes parameter
        if params.goniometer.axes is not None:
            if len(params.goniometer.axes) % 3:
                raise RuntimeError(
                    "Number of values for axes parameter must be multiple of 3."
                )

        # Check the fixed rotation
        if params.goniometer.fixed_rotation is not None:
            raise RuntimeError("Multi-axis goniometer requires fixed_rotation == None")

        # Check the setting rotation
        if params.goniometer.setting_rotation is not None:
            raise RuntimeError(
                "Multi-axis goniometer requires setting_rotation == None"
            )

        # Check the input
        if reference is None:
            if params.goniometer.axes is None:
                raise RuntimeError("No axes set")

            # Create the axes
            axes = flex.vec3_double(
                params.goniometer.axes[i * 3 : (i * 3) + 3]
                for i in range(len(params.goniometer.axes) // 3)
            )

            # Invert the rotation axis
            if params.goniometer.invert_rotation_axis is True:
                axes = flex.vec3_double([[-x for x in v] for v in axes])

            # Create the angles
            if params.goniometer.angles is not None:
                angles = params.goniometer.angles
                if len(angles) != len(axes):
                    raise RuntimeError("Number of angles must match axes")
            else:
                angles = flex.double([0] * len(axes))

            # Create the names
            if params.goniometer.names is not None:
                names = params.goniometer.names
                if len(names) != len(axes):
                    raise RuntimeError("Number of names must match axes")
            else:
                names = flex.std_string([""] * len(axes))

            # Create the scan axis
            if params.goniometer.scan_axis is not None:
                scan_axis = params.goniometer.scan_axis
            else:
                scan_axis = 0

            # Create the model
            goniometer = MultiAxisGoniometer(axes, angles, names, scan_axis)
        else:
            goniometer = reference

            # Set the axes
            if params.goniometer.axes is not None:
                axes = flex.vec3_double(
                    params.goniometer.axes[i * 3 : (i * 3) + 3]
                    for i in range(len(params.goniometer.axes) // 3)
                )
                if len(goniometer.get_axes()) != len(axes):
                    raise RuntimeError(
                        "Number of axes must match the current goniometer (%s)"
                        % len(goniometer.get_axes())
                    )
                goniometer.set_axes(axes)

            # Invert rotation axis
            if params.goniometer.invert_rotation_axis is True:
                axes = flex.vec3_double(
                    [[-x for x in v] for v in goniometer.get_axes()]
                )
                goniometer.set_axes(axes)

            # Set the angles
            if params.goniometer.angles is not None:
                if len(goniometer.get_angles()) != len(params.goniometer.angles):
                    raise RuntimeError(
                        "Number of angles must match the current goniometer (%s)"
                        % len(goniometer.get_angles())
                    )
                goniometer.set_angles(params.goniometer.angles)

            # Set the namess
            if params.goniometer.names is not None:
                if len(goniometer.get_names()) != len(params.goniometer.names):
                    raise RuntimeError(
                        "Number of names must match the current goniometer (%s)"
                        % len(goniometer.get_names())
                    )
                goniometer.set_names(params.goniometer.names)

            # Set the scan axis
            if params.goniometer.scan_axis is not None:
                raise RuntimeError("Can not override scan axis")

        return goniometer

    @staticmethod
    def from_phil(params, reference=None):
        """
        Convert the phil parameters into a goniometer model

        """
        if params.goniometer.axis and params.goniometer.axes:
            raise ValueError("Only one of axis or axes should be set")
        if reference is not None:
            if isinstance(reference, MultiAxisGoniometer):
                goniometer = GoniometerFactory.multi_axis_goniometer_from_phil(
                    params, reference
                )
            else:
                goniometer = GoniometerFactory.single_axis_goniometer_from_phil(
                    params, reference
                )
        else:
            if params.goniometer.axes and len(params.goniometer.axes) > 3:
                goniometer = GoniometerFactory.multi_axis_goniometer_from_phil(params)
            elif params.goniometer.axis or params.goniometer.axes:
                goniometer = GoniometerFactory.single_axis_goniometer_from_phil(params)
            else:
                return None
        return goniometer

    @staticmethod
    def from_dict(d, t=None):
        """Convert the dictionary to a goniometer model

        Params:
            d The dictionary of parameters
            t The template dictionary to use

        Returns:
            The goniometer model
        """
        if d is None and t is None:
            return None
        joint = t.copy() if t else {}
        joint.update(d)

        # Create the model from the joint dictionary
        if {"axes", "angles", "scan_axis"}.issubset(joint):
            return MultiAxisGoniometer.from_dict(joint)
        return Goniometer.from_dict(joint)

    @staticmethod
    def make_goniometer(rotation_axis, fixed_rotation):
        return Goniometer(
            tuple(map(float, rotation_axis)), tuple(map(float, fixed_rotation))
        )

    @staticmethod
    def make_kappa_goniometer(alpha, omega, kappa, phi, direction, scan_axis):
        omega_axis = (1, 0, 0)
        phi_axis = (1, 0, 0)

        c = math.cos(alpha * math.pi / 180)
        s = math.sin(alpha * math.pi / 180)
        if direction == "+y":
            kappa_axis = (c, s, 0.0)
        elif direction == "+z":
            kappa_axis = (c, 0.0, s)
        elif direction == "-y":
            kappa_axis = (c, -s, 0.0)
        elif direction == "-z":
            kappa_axis = (c, 0.0, -s)
        else:
            raise RuntimeError("Invalid direction")

        if scan_axis == "phi":
            scan_axis = 0
        else:
            scan_axis = 2

        axes = flex.vec3_double((phi_axis, kappa_axis, omega_axis))
        angles = flex.double((phi, kappa, omega))
        names = flex.std_string(("PHI", "KAPPA", "OMEGA"))
        return GoniometerFactory.make_multi_axis_goniometer(
            axes, angles, names, scan_axis
        )

    @staticmethod
    def make_multi_axis_goniometer(axes, angles, names, scan_axis):
        return MultiAxisGoniometer(axes, angles, names, scan_axis)

    @staticmethod
    def single_axis():
        """Construct a single axis goniometer which is canonical in the
        CBF reference frame."""

        axis = (1, 0, 0)
        fixed = (1, 0, 0, 0, 1, 0, 0, 0, 1)

        return GoniometerFactory.make_goniometer(axis, fixed)

    @staticmethod
    def single_axis_reverse():
        """Construct a single axis goniometer which is canonical in the
        CBF reference frame, but reversed in rotation."""

        axis = (-1, 0, 0)
        fixed = (1, 0, 0, 0, 1, 0, 0, 0, 1)

        return GoniometerFactory.make_goniometer(axis, fixed)

    @staticmethod
    def known_axis(axis):
        """Return an goniometer instance for a known rotation axis, assuming
        that nothing is known about the fixed element of the rotation axis."""

        assert len(axis) == 3

        fixed = (1, 0, 0, 0, 1, 0, 0, 0, 1)

        return Goniometer(axis, fixed)

    @staticmethod
    def kappa(alpha, omega, kappa, phi, direction, scan_axis):
        """Return a kappa goniometer where omega is the primary axis (i,e.
        aligned with X in the CBF coordinate frame) and has the kappa arm
        with angle alpha attached to it, aligned with -z, +y, +z or -y at
        omega = 0, that being the direction, which in turn has phi fixed to it
        which should initially be coincident with omega. We also need to know
        which axis is being used for the scan i.e. phi or omega. All angles
        should be given in degrees. This will work by first constructing the
        rotation axes and then composing them to the scan axis and fixed
        component of the rotation."""

        return GoniometerFactory.make_kappa_goniometer(
            alpha, omega, kappa, phi, direction, scan_axis
        )

    @staticmethod
    def multi_axis(axes, angles, names, scan_axis):
        """ """

        return GoniometerFactory.make_multi_axis_goniometer(
            axes, angles, names, scan_axis
        )

    @staticmethod
    def imgCIF(cif_file):
        """Initialize a goniometer model from an imgCIF file."""

        # FIXME in here work out how to get the proper setting matrix if != 1

        cbf_handle = pycbf.cbf_handle_struct()
        cbf_handle.read_file(cif_file.encode(), pycbf.MSG_DIGEST)

        return GoniometerFactory.imgCIF_H(cbf_handle)

    @staticmethod
    def imgCIF_H(cbf_handle):
        """Initialize a goniometer model from an imgCIF file handle, where
        it is assumed that the file has already been read."""

        # find the goniometer axes and dependencies
        dependants = {}
        axis_vectors = {}
        angles = {}
        scan_axis = None
        cbf_handle.find_category(b"axis")
        for i in range(cbf_handle.count_rows()):
            cbf_handle.find_column(b"equipment")
            if cbf_handle.get_value() == b"goniometer":
                cbf_handle.find_column(b"id")
                axis_name = cbf_handle.get_value().decode()
                axis_vector = []
                for i in range(3):
                    cbf_handle.find_column(b"vector[%i]" % (i + 1))
                    axis_vector.append(float(cbf_handle.get_value()))
                axis_vectors[axis_name] = axis_vector
                cbf_handle.find_column(b"depends_on")
                dependants[cbf_handle.get_value().decode()] = axis_name
            cbf_handle.next_row()

        # find the starting angles of each goniometer axis and figure out which one
        # is the scan axis (i.e. non-zero angle_increment)
        cbf_handle.find_category(b"diffrn_scan_axis")
        for i in range(cbf_handle.count_rows()):
            cbf_handle.find_column(b"axis_id")
            axis_name = cbf_handle.get_value().decode()
            if axis_name not in axis_vectors:
                cbf_handle.next_row()
                continue
            cbf_handle.find_column(b"angle_start")
            axis_angle = float(cbf_handle.get_value())
            cbf_handle.find_column(b"angle_increment")
            increment = float(cbf_handle.get_value())
            angles[axis_name] = axis_angle
            if increment != 0:
                if scan_axis:
                    raise ValueError(
                        "More than one scan axis is defined: not currently supported."
                    )
                scan_axis = axis_name
            cbf_handle.next_row()
        if not len(axis_vectors) == len(angles):
            raise ValueError(
                "The number of goniometer axes specified in the 'axis' category of the "
                "raw data does not match the number specified in the "
                "'diffrn_scan_axis' category."
            )

        # figure out the order of the axes from the depends_on values
        ordered_axes = []
        axis = dependants.get(".")
        while axis:
            ordered_axes.append(axis)
            axis = dependants.get(axis)

        # multi-axis gonio requires axes in order as viewed from crystal to gonio base
        # i.e. the reverse of the order we have from cbf header
        ordered_axes = ordered_axes[::-1]
        axis_vectors = flex.vec3_double(axis_vectors[axis] for axis in ordered_axes)
        angles = flex.double(angles[axis] for axis in ordered_axes)
        # If no scan_axis, probably a still shot ⇒ scan axis arbitrary, set to 0.
        scan_axis = ordered_axes.index(scan_axis) if scan_axis else 0

        # construct a multi-axis goniometer
        gonio = GoniometerFactory.multi_axis(
            axis_vectors, angles, flex.std_string(ordered_axes), scan_axis
        )
        return gonio
