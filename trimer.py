#!/usr/bin/env python
""" Script to setup trimer for an interactive hoomd session"""
#
# Malcolm Ramsay 2016-03-09
#

# Hoomd helper functions

import math
import numpy as np
import hoomd
from hoomd import md
from hoomd import deprecated

# This sets up the processing configuration for the simulation run,
# looking for GPUs, MPI etc.
hoomd.context.initialize()

# We want to run a simulation in 2D, so restrict positions to 0 in the z
# direction
md.update.enforce2d()

# Create a 2D square lattice of 50x50 with particles of type A on the lattice
# points. This will be all the central particles of the molecules we are
# creating, the rest will be defined later in the script.
system = hoomd.init.create_lattice(unitcell=hoomd.lattice.sq(a=4), n=[50, 50])

# Set moments of inertia for every central particle. This is what hoomd uses to
# determine if there are rotational degrees of freedom it is going to integrate.
# The moment of inertia is given as a tuple (Lx, Ly, Lz)
for particle in system.particles:
    if particle.type == 'A':
        particle.moment_inertia = (0, 0, 1.65)

# Define a second type of particle
system.particles.types.add('B')

# Set interaction potentials for all interaction types
potentials = md.pair.lj(r_cut=2.5, nlist=md.nlist.cell())
potentials.pair_coeff.set('A', 'A', epsilon=1, sigma=2)
potentials.pair_coeff.set('B', 'B', epsilon=1, sigma=0.637556*2)
potentials.pair_coeff.set('A', 'B', epsilon=1, sigma=1.637556)

# Define rigid bodies.
rigid = md.constrain.rigid()

# Each rigid body centered on the particles of type A has two particles
# of type B at the given relative coordinates
rigid.set_param('A', positions=[(math.sin(math.pi/3),
                                 math.cos(math.pi/3), 0),
                                (-math.sin(math.pi/3),
                                 math.cos(math.pi/3), 0)],
                types=['B', 'B']
               )

# Create the rigid bodies in the simulation, in this case we want to create the
# additional particles that comprise the rigid bodies, hence create=True.
rigid.create_bodies(create=True)

# Create a group of particles only referencing the central rigid bodies, this
# is the group we use for integration.
center = hoomd.group.rigid_center()

# Output thermodynamic data to a file out.dat every 1000 steps.
thermo = hoomd.analyze.log(
    filename="out.dat",
    quantities=[
        'temperature',
        'pressure',
        'volume',
        'translational_kinetic_energy',
        'rotational_kinetic_energy',
        'rotational_ndof',
        'translational_ndof',
        'N'
    ],
    period=1000
)

# Set integration parameters
md.integrate.mode_standard(dt=0.001)
npt = md.integrate.npt(
    group=center,
    kT=2.0,
    tau=5,
    P=13.5,
    tauP=5
)

hoomd.run(10000)

# Increase step size and decrease Nose-Hoover imaginary mass
md.integrate.mode_standard(dt=0.005)
npt.set_params(tau=1, tauP=1)

# To monitor the Simulation in real time you need to output an xml file to read
# into vmd as the initial configuration.
# xml = deprecated.dump.xml(filename="out.xml", group=hoomd.group.all(), all=True)
# xml.write("out.xml")
# Send snapshots to VMD in real time using port 4321 sending snapshots
# every 100 timesteps (approx 20 per second on artemis)
# hoomd.analyze.imd( port=4321, period=200,)

hoomd.run(100000)
