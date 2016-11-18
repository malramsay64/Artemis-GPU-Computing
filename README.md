Using GPUs on Artemis
=====================

With the current underutilisation of the GPU nodes on Artemis and the plan to bring more GPU compute power to the School of Chemistry, this serves as an introduction to using these resources using [Hoomd](http://glotzerlab.engin.umich.edu/hoomd-blue/index.html) as a sample use case.


Requesting Resources on Artemis
-------------------------------

With the upgrade to Artemis there has been a change to the way jobs are selected with some functionality no longer available and requirements for requesting memory. The command for requesting an interactive job now looks like this:

    qsub -l select=1:ncpus=1:mem=16gb -l walltime=4:00:00 -P <project> -I

Here we are selecting 1 'chunk', where the 'chunk' consists of 1 cpu and 16 Gb of RAM. If we want 16 cores, we could either run 

    echo "cat \$PBS_NODES > nodes.txt" | qsub -l select=1:ncpus=16:mem=256gb -l walltime=4:00:00 -P <project>

or 

    echo "cat \$PBS_NODES > nodes.txt" | qsub -l select=16:ncpus=1:mem=16gb -l walltime=4:00:00 -P <project>

The first of which will select 16 cores on a single node, while the second will select 16 cpus amongst any available across all the nodes.

### Requesting a GPU resources

Requesting GPU resources is much the same as CPU resources, simply;

    qsub -l select=1:ncpus=1:ngpus=1:mem=16gb -l walltime=4:00:00 -P <project> -I

which will request an interactive session with 1 GPU. This puts the job on the GPU queue which only runs on nodes `hpc211 - hpc215` which are the nodes housing the GPUs.

Once you have accessed a GPU node, to run any CUDA software you will need to load the CUDA runtime libraries.

    $ module load cuda

Hoomd
-----

[Hoomd](http://glotzerlab.engin.umich.edu/hoomd-blue/index.html) is a molecular dynamics software package designed to be run on a GPU. Since it is designed from the ground up for GPU simulations there is a significant performance improvement when using the GPU.

### Benchmarks

As an example of the speed up exhibited when using the GPU the below table shows results from running a [standard lj-liquid benchmark](http://nbviewer.jupyter.org/github/joaander/hoomd-benchmarks/blob/master/lj-liquid.ipynb) of 64000 particles on a single node of Artemis.

| Num GPUs  | Num Threads | TPS  | Speed Up |
| --------- | ----------  | ---- | -------  |
| 1         | 1           | 879  | 4.08     |
| 2         | 2           | 1155 | 5.37     |
| 2         | 4           | 677  | 3.14     |
| 0         | 24          | 215  | 1.00     |


### Installation

Installing Hoomd is as simple as running

    $ conda config --add channels glotzer
    $ conda install hoomd

This is assuming that some version of conda is installed (Download links and instructions [here](http://conda.pydata.org/miniconda.html)). To use GPUs with this method requires CUDA Runtime 7.5, which is the version loaded by default on Artemis.


Running Simulations
-------------------

Hoomd runs in a python environment, allowing us to use all the available python tools to dynamically alter the simulation, or to compute values from the simulation. The file [trimer.hoomd](trimer.hoomd) is a sample simulation using Mickey Mouse like trimer molecules.

    $ python trimer.py

Since Hoomd is running a python environment we can use the python interactive mode to interact with the simulation while it is running. Passing the `-i` flag will run the code in the script and then wait for user input.

    $ python -i trimer.py

There is currently a bug in Hoomd when equilibrating pressure for this system. We are going to check that my solution of dividing the target pressure by 2.2 gives the desired equilibration pressure. I have set up an `analyzer` in the [trimer.hoomd](trimer.hoomd) script that we can query using

    > thermo.query('temperature')
    > thermo.query('pressure')

The instantaneous values we get from this should be relatively close to our target values, however we want some statistics.

    > t_values = []
    > p_values = []
    > for i in range(100):
    .   run(1000)
    .   t_values.append(thermo.query('temperature'))
    .   t_values.append(thermo.query('pressure'))
    .
    > np.mean(t_values)
    2.0...
    > np.mean(p_values)
    13.6...

A further benefit of having a python scripting environment is that all the simulation parameters are available for querying during the simulation. To calculate the Mean Squared Displacement

    > s1 = hoomd.system.take_snapshot()
    > hoomd.run(1000)
    > s2 = hoomd.system.take_snapshot()
    > np.power(s2.particles.position - s1.particles.position, 2).sum(axis=1)

Simulation Visualisation
------------------------

Making a good picture of a simulation is hugely informative, how about creating a movie. Hoomd has a function that will allow Interactive Molecular Dynamics (imd) which will update a configuration in VMD for a real time view of the simulation.

Getting this working on a local machine is a reasonably simple process. 

1. Get Hoomd to send imd snapshots to a port. This has already been done in [trimer.hoomd](trimer.hoomd)

        > hoomd.analyze.imd(port=4321, rate=100)

2. Set the simulation running for a reasonable period of time (1 minute or more). 1 million timesteps should work.

        > hoomd.run(1000000)

3. In a separate terminal load the initial configuration xml file (trimer.xml) into VMD

        $ vmd -hoomd trimer.xml

4. Connect VMD to the port opened by hoomd.

        > imd connect localhost 4321

This should result in the configuration in VMD updating in real time.


### IMD with Artemis

While a little more complicated, running a simulation on Artemis while viewing in VMD is definitely possible. It is fundamentally the same as for a local machine however we have to set up an ssh tunnel between our local machine and the node the simulation is running on.

1. Work out which node the simulation is running on.
    1. In an interactive session this is simply running the `hostname` command
    2. For a batch script knowing your `<job id>` run `pbs-nodes -a | grep -C6 <job id>` which should have the node at the top
2. Create an ssh tunnel from the local machine to the node through artemis

        $ ssh -L 4321:<compute node>:4321 -N hpc.sydney.edu.au

3. Run VMD as per a local session

