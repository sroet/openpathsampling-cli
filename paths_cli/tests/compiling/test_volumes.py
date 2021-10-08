import pytest
from unittest import mock
from paths_cli.tests.compiling.utils import mock_compiler

import yaml
import openpathsampling as paths
from openpathsampling.tests.test_helpers import make_1d_traj

from paths_cli.compiling.volumes import *

class TestBuildCVVolume:
    def setup(self):
        self.yml = "\n".join(["type: cv-volume", "cv: {func}",
                              "lambda_min: 0", "lambda_max: 1"])

        self.mock_cv = mock.Mock(return_value=0.5)
        self.named_objs_dict = {
            'foo': {'name': 'foo',
                    'type': 'bar',
                    'func': 'foo_func'}
        }

        self.func = {
            'inline': "\n  ".join(["name: foo", "type: mdtraj"]),
            'external': 'foo'
        }

    def create_inputs(self, inline, periodic):
        yml = "\n".join(["type: cv-volume", "cv: {func}",
                         "lambda_min: 0", "lambda_max: 1"])

    def set_periodic(self, periodic):
        if periodic == 'periodic':
            self.named_objs_dict['foo']['period_max'] = 'np.pi'
            self.named_objs_dict['foo']['period_min'] = '-np.pi'

    @pytest.mark.parametrize('inline', ['external', 'external'])
    @pytest.mark.parametrize('periodic', ['periodic', 'nonperiodic'])
    def test_build_cv_volume(self, inline, periodic):
        self.set_periodic(periodic)
        yml = self.yml.format(func=self.func[inline])
        dct = yaml.load(yml, Loader=yaml.FullLoader)
        if inline =='external':
            patch_loc = 'paths_cli.compiling.root_compiler._COMPILERS'
            compilers = {
                'cv': mock_compiler('cv', named_objs={'foo': self.mock_cv})
            }
            with mock.patch.dict(patch_loc, compilers):
                vol = build_cv_volume(dct)
        elif inline == 'internal':
            vol = build_cv_volume(dct)
        assert vol.collectivevariable(1) == 0.5
        expected_class = {
            'nonperiodic': paths.CVDefinedVolume,
            'periodic': paths.PeriodicCVDefinedVolume
        }[periodic]
        assert isinstance(vol, expected_class)


class TestBuildCombinationVolume:
    def setup(self):
        from  openpathsampling.experimental.storage.collective_variables \
                import CollectiveVariable
        self.cv = CollectiveVariable(lambda s: s.xyz[0][0]).named('foo')

    def _vol_and_yaml(self, lambda_min, lambda_max, name):
        yml = ['- type: cv-volume', '  cv: foo',
               f"  lambda_min: {lambda_min}",
               f"  lambda_max: {lambda_max}"]
        vol = paths.CVDefinedVolume(self.cv, lambda_min,
                                    lambda_max).named(name)
        description = {'name': name,
                       'type': 'cv-volume',
                       'cv': 'foo',
                       'lambda_min': lambda_min,
                       'lambda_max': lambda_max}
        return vol, yml, description

    @pytest.mark.parametrize('combo', ['union', 'intersection'])
    @pytest.mark.parametrize('inline', [True, False])
    def test_build_combo_volume(self, combo, inline):
        vol_A, yaml_A, desc_A = self._vol_and_yaml(0.0, 0.55, "A")
        vol_B, yaml_B, desc_B = self._vol_and_yaml(0.45, 1.0, "B")
        if inline:
            named_volumes_dict = {}
            descriptions = {}
            subvol_yaml = ['  ' + line for line in yaml_A + yaml_B]
        else:
            named_volumes_dict = {v.name: v for v in [vol_A, vol_B]}
            descriptions = {"A": desc_A, "B": desc_B}
            subvol_yaml = ['  - A', '  - B']

        yml = "\n".join([f"type: {combo}", "name: bar", "subvolumes:"]
                        + subvol_yaml)

        combo_class = {'union': paths.UnionVolume,
                       'intersection': paths.IntersectionVolume}[combo]
        builder = {'union': build_union_volume,
                   'intersection': build_intersection_volume}[combo]

        true_vol = combo_class(vol_A, vol_B)
        dct = yaml.load(yml, yaml.FullLoader)
        compiler = {
            'cv': mock_compiler('cv', named_objs={'foo': self.cv}),
            'volume': mock_compiler(
                'volume',
                type_dispatch={'cv-volume': build_cv_volume},
                named_objs=named_volumes_dict
            ),
        }
        with mock.patch.dict('paths_cli.compiling.root_compiler._COMPILERS',
                             compiler):
            vol = builder(dct)

        traj = make_1d_traj([0.5, 2.0, 0.2])
        assert vol(traj[0])
        assert not vol(traj[1])
        assert vol(traj[2]) == (combo == 'union')