from paths_cli.wizard.engines import engines
from paths_cli.compiling.tools import custom_eval, mdtraj_parse_atomlist
from paths_cli.wizard.load_from_ops import load_from_ops
from paths_cli.wizard.load_from_ops import LABEL as _load_label
from paths_cli.wizard.core import get_object

from functools import partial
import numpy as np

try:
    import mdtraj as md
except ImportError:  # no-cov
    HAS_MDTRAJ = False
else:
    HAS_MDTRAJ = True

def mdtraj_atom_helper(wizard, user_input, n_atoms):  # no-cov
    wizard.say("You should specify atom indices enclosed in double "
               "brackets, e.g, [" + str(list(range(n_atoms))) + "]")
    # TODO: implement the following:
    # wizard.say("You can specify atoms either as atom indices (which count "
               # "from zero) or as atom labels of the format "
               # "CHAIN:RESIDUE-ATOM, e.g., '0:ALA1-CA' for the alpha carbon "
               # "of alanine 1 (this time counting from one, as in the PDB) "
               # "of the 0th chain in the topology. You can also use letters "
               # "for chain IDs, but note that A corresponds to the first "
               # "chain in your topology, even if its name in the PDB file "
               # "is B.")

def _get_topology(wizard):
    from paths_cli.wizard.engines import engines
    topology = None
    # TODO: this is very similar to get_missing_object, but has more
    # reporting; is there some way to add the reporting to
    # get_missing_object?
    if len(wizard.engines) == 0:
        # SHOULD NEVER GET HERE IF WIZARDS ARE DESIGNED CORRECTLY
        wizard.say("Hey, you need to define an MD engine before you "
                   "create CVs that refer to it. Let's do that now!")
        engine = engines(wizard)
        wizard.register(engine, 'engine', 'engines')
        wizard.say("Now let's get back to defining your CV.")
        topology = engine.topology
    elif len(wizard.engines) == 1:
        topology = list(wizard.engines.values())[0].topology
    else:
        wizard.say("You have defined multiple engines, and need to pick "
                   "one to use to get a the topology for your CV.")
        engine = wizard.obj_selector('engines', 'engine', engines)
        topology = engine.topology
        wizard.say("Now let's get back to defining your CV.")

    return topology

@get_object
def _get_atom_indices(wizard, topology, n_atoms, cv_user_str):
    helper = partial(mdtraj_atom_helper, n_atoms=n_atoms)
    # switch to get_custom_eval
    atoms_str = wizard.ask(f"Which atoms do you want to {cv_user_str}?",
                           helper=helper)
    try:
        arr = mdtraj_parse_atomlist(atoms_str, n_atoms, topology)
    except Exception as e:
        wizard.exception(f"Sorry, I didn't understand '{atoms_str}'.", e)
        mdtraj_atom_helper(wizard, '?', n_atoms)
        return

    return arr


def _mdtraj_function_cv(wizard, cv_does_str, cv_user_prompt, func,
                        kwarg_name, n_atoms, period):
    from openpathsampling.experimental.storage.collective_variables import \
            MDTrajFunctionCV
    wizard.say(f"We'll make a CV that measures the {cv_does_str}.")
    period_min, period_max = period
    topology = _get_topology(wizard)
    indices = _get_atom_indices(wizard, topology, n_atoms=n_atoms,
                                cv_user_str=cv_user_prompt)
    kwargs = {kwarg_name: indices}
    atoms_str = " ".join([str(topology.mdtraj.atom(i)) for i in indices[0]])

    summary = ("Here's what we'll create:\n"
               f"  Function: {func.__name__}\n"
               f"     Atoms: {atoms_str}\n"
               f"  Topology: {repr(topology.mdtraj)}")
    wizard.say(summary)

    return MDTrajFunctionCV(func, topology, period_min=period_min,
                            period_max=period_max, **kwargs)

def distance(wizard):
    return _mdtraj_function_cv(
        wizard=wizard,
        cv_does_str="distance between two atoms",
        cv_user_prompt="measure the distance between",
        func=md.compute_distances,
        kwarg_name='atom_pairs',
        n_atoms=2,
        period=(None, None)
    )

def angle(wizard):
    return _mdtraj_function_cv(
        wizard=wizard,
        cv_does_str="angle made by three atoms",
        cv_user_prompt="use to define the angle",
        func=md.compute_angles,
        kwarg_name='angle_indices',
        n_atoms=3,
        period=(-np.pi, np.pi)
    )

def dihedral(wizard):
    return _mdtraj_function_cv(
        wizard=wizard,
        cv_does_str="dihedral made by four atoms",
        cv_user_prompt="use to define the dihedral angle",
        func=md.compute_dihedrals,
        kwarg_name='indices',
        n_atoms=4,
        period=(-np.pi, np.pi)
    )

def rmsd(wizard):
    raise NotImplementedError("RMSD has not yet been implemented")

def coordinate(wizard):
    # TODO: atom_index should be from wizard.ask_custom_eval
    from openpathsampling.experimental.storage.collective_variables import \
            CoordinateFunctionCV
    atom_index = coord = None
    while atom_index is None:
        idx = wizard.ask("For which atom do you want to get the "
                         "coordinate? (counting from zero)")
        try:
            atom_index = int(idx)
        except Exception as e:
            wizard.exception("Sorry, I can't make an atom index from "
                             f"'{idx}'", e)

    while coord is None:
        xyz = wizard.ask("Which coordinate (x, y, or z) do you want for "
                         f"atom {atom_index}?")
        try:
            coord = {'x': 0, 'y': 1, 'z': 2}[xyz]
        except KeyError as e:
            wizard.bad_input("Please select one of 'x', 'y', or 'z'")

    cv = CoordinateFunctionCV(lambda snap: snap.xyz[atom_index][coord])
    return cv


SUPPORTED_CVS = {}

if HAS_MDTRAJ:
    SUPPORTED_CVS.update({
        'Distance': distance,
        'Angle': angle,
        'Dihedral': dihedral,
        # 'RMSD': rmsd,
    })

SUPPORTED_CVS.update({
    'Coordinate': coordinate,
    # 'Python script': ...,
    _load_label: partial(load_from_ops,
                         store_name='cvs',
                         obj_name='CV'),
})

def cvs(wizard):
    wizard.say("You'll need to describe your system in terms of "
               "collective variables (CVs). We'll use these to define "
               "things like stable states.")
    cv_names = list(SUPPORTED_CVS.keys())
    cv_type = wizard.ask_enumerate("What kind of CV do you want to "
                                   "define?", options=cv_names)
    cv = SUPPORTED_CVS[cv_type](wizard)
    return cv

if __name__ == "__main__":  # no-cov
    from paths_cli.wizard.wizard import Wizard
    wiz = Wizard({})
    cvs(wiz)