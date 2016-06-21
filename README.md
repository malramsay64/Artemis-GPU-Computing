Using GPUs on Artemis
=====================

With the current underutilisation of the GPU nodes on Artemis and the plan to bring more GPU compute power to the School of Chemistry, this serves as an introduction to using these resources using [Hoomd](http://glotzerlab.engin.umich.edu/hoomd-blue/index.html) as a sample use case.

Requesting a GPU node
---------------------

Submitting a job to a GPU node essentially the same as submitting any other job, with the addition of the `-q gpu` flag where `interactive.pbs` is the base script in this [repository](interactive.pbs).

    $ qsub -q gpu interactive.pbs

This puts the job on the GPU queue which only runs on nodes `hpc211 - hpc215` which are the nodes housing the GPUs.

Once you have accessed a GPU node, to run any CUDA software you will need to load the CUDA runtime libraries.

    $ module load cuda


It is worth noting that the GPUs on Artemis are less managed than the CPUs, where you can request the number of CPUs you require. For GPUs, as long as you have access to a node then you have access to the GPUs regardless of the number of cores you requested. This means that if you submit a number of single core jobs requesting a single GPU each then there will potentially be 12 jobs trying to run on the same GPU, slowing everything down. The current solution to this is to either request an entire node `-l nodes=1:ppn=24` or hope that the other jobs running on the node aren't also running on the GPU.

I suggest that for running Hoomd simulations on a single GPU that we request half a node (`-l nodes=1:ppn=12`) since Hoomd will look for the least utilised GPU in the system and run on that.

### Troubleshooting GPUs

I am fairly certain that very few people have been using the GPUs on Artemis since on two occasions I have had to log a ticket to run a job on them. Since it is likely there will be issues a set of troubleshooting guidelines. These steps apply to any NVIDIA compute system.

1. To check that there are actually GPUs connected and you are on a GPU node, if there are NVIDIA GPUs connected there should be a response. The following shows the two Tesla K40m cards connected to a GPU node.

```
$ lspci | grep -i nvidia
03:00.0 3D controller: NVIDIA Corporation GK110BGL [Tesla K40m] (rev a1)
82:00.0 3D controller: NVIDIA Corporation GK110BGL [Tesla K40m] (rev a1)
```

2. Checking the driver versions of the cards, as well as their utilisation. If there are jobs running you will see them under the compute processes.

```
$ nvidia-smi
+------------------------------------------------------+                       
| NVIDIA-SMI 340.65     Driver Version: 340.65         |                       
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  Tesla K40m          Off  | 0000:03:00.0     Off |                    0 |
| N/A   32C    P0    59W / 235W |     55MiB / 11519MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
|   1  Tesla K40m          Off  | 0000:82:00.0     Off |                    0 |
| N/A   34C    P0    68W / 235W |     55MiB / 11519MiB |    100%      Default |
+-------------------------------+----------------------+----------------------+
+-----------------------------------------------------------------------------+
| Compute processes:                                               GPU Memory |
|  GPU       PID  Process name                                     Usage      |
|=============================================================================|
|  No running compute processes found                                         |
+-----------------------------------------------------------------------------+
```

3. Ensure that the CUDA Runtime can communicate with the GPUs.

```
$ module load cuda
$ deviceQuery | grep ^Result
Result = PASS
```

The `deviceQuery` program can be used to get a wide array of information about the GPU including; dri version compatibility, compute capability, ECC support. Essentially it has everything you might want to know about the GPU. This tool is part of the CUDA Samples package and needs to be compiled, however it is loaded into the `$PATH` when CUDA is loaded on Artemis.


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

Hoomd is already installed on Artemis and can be loaded using

    $ module load hoomd
    $ module load cuda

Along with the default Hoomd module, there is also a python 3 version which can be loaded using

    $ module load hoomd/1.3.3-python3
    $ module load cuda

To run on the GPU the CUDA module also needs to be loaded along with Hoomd.

#### Compiling on Artemis

To compile Hoomd on Artemis for whatever reason the following set of commands should work.

    $ module purge
    $ module load cuda/6.5.14-test boost/1.57.0 python/2.7.9 cmake/3.4.0 gcc/4.8.4
    $ git clone https://bitbucket.org/glotzer/hoomd-blue.git
    $ cd hoomd-blue; mkdir build; cd build
    $ install_dir=$HOME/.local/hoomd/1.3.3
    $ cmake -DCMAKE_BUILD_TYPE=release -DCMAKE_INSTALL_PREFIX="$install_dir" ..
    $ make -j24
    $ make test
    $ make install

#### Installing like a Sane Person

Installing Hoomd on another computer is as simple as running

    $ conda config --add channels glotzer
    $ conda install hoomd

This is assuming that some version of conda is installed (Download links and instructions [here](http://conda.pydata.org/miniconda.html)). To use GPUs with this method requires CUDA Runtime 7.5, which is the latest version.


Running Simulations
-------------------

Hoomd runs in a python environment, allowing us to use all the available python tools to dynamically alter the simulation, or to compute values from the simulation. The file [trimer.hoomd](trimer.hoomd) is a sample simulation using Mickey Mouse like trimer molecules.

    $ hoomd trimer.hoomd

Since Hoomd is running a python environment we can use the python interactive mode to interact with the simulation while it is running. Passing the `-i` flag will run the code in the script and then wait for user input.

    $ hoomd -i trimer.hoomd

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

    > s1 = system.take_snapshot()
    > run(1000)
    > s2 = system.take_snapshot()
    > np.power(s2.particles.position - s1.particles.position, 2).sum(axis=1)

Simulation Visualisation
------------------------

Making a good picture of a simulation is hugely informative, how about creating a movie. Hoomd has a function that will allow Interactive Molecular Dynamics (imd) which will update a configuration in VMD for a real time view of the simulation.

Getting this working on a local machine is a reasonably simple process. 

1. Get Hoomd to send imd snapshots to a port. This has already been done in [trimer.hoomd](trimer.hoomd)

        > analyze.imd(port=54321, rate=100)

2. Set the simulation running for a reasonable period of time (1 minute or more). 1 million timesteps should work.

        > run(1000000)

3. In a separate terminal load the initial configuration xml file (trimer.xml) into VMD

        $ vmd -hoomd trimer.xml

4. Connect VMD to the port opened by hoomd.

        > imd connect localhost 54321

This should result in the configuration in VMD updating in real time.


### IMD with Artemis

While a little more complicated, running a simulation on Artemis while viewing in VMD is definitely possible. It is fundamentally the same as for a local machine however we have to set up an ssh tunnel between our local machine and the node the simulation is running on.

1. Work out which node the simulation is running on.
    1. In an interactive session this is simply running the `hostname` command
    2. For a batch script knowing your `<job id>` run `pbs-nodes -a | grep -C6 <job id>` which should have the node at the top
2. Create an ssh tunnel from the local machine to the node through artemis

        $ ssh -L 54321:<compute node>:54321 -N hpc.sydney.edu.au

3. Run VMD as per a local session

