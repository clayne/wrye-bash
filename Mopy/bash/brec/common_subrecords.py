# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <https://www.gnu.org/licenses/>.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Builds on the basic elements defined in base_elements.py to provide
definitions for some commonly needed subrecords."""
from collections import defaultdict
from itertools import chain

from .advanced_elements import AttrValDecider, MelArray, MelTruncatedStruct, \
    MelUnion, PartialLoadDecider, FlagDecider, MelSorted, MelSimpleArray, \
    MelCounter
from .basic_elements import MelBase, MelFid, MelGroup, MelGroups, MelLString, \
    MelNull, MelSequential, MelString, MelStruct, MelUInt32, MelOptStruct, \
    MelFloat, MelReadOnly, MelFids, MelUInt32Flags, MelUInt8Flags, MelSInt32, \
    MelStrings, MelUInt8, MelUInt16Flags
from .utils_constants import int_unpacker, FID, null1
from ..bolt import Flags, encode, struct_pack, struct_unpack, unpack_byte, \
    dict_sort, TrimmedFlags, structs_cache
from ..exception import ModError, ModSizeError

#------------------------------------------------------------------------------
class MelActiFlags(MelUInt16Flags):
    """Handles the FNAM (Flags) subrecord in ACTI records."""
    _acti_flags = Flags.from_names(
        (0, 'no_displacement'),
        (1, 'ignored_by_sandbox'),
        (4, 'is_a_radio'), # Introduced in FO4
    )

    def __init__(self):
        super().__init__(b'FNAM', 'acti_flags', self._acti_flags)

#------------------------------------------------------------------------------
class MelActionFlags(MelUInt32Flags):
    """XACT (Action Flags) subrecord for REFR records."""
    _act_flags = Flags.from_names('act_use_default', 'act_activate',
                                  'act_open', 'act_open_by_default')

    def __init__(self):
        super().__init__(b'XACT', 'action_flags', self._act_flags)

    ##: HACK - right solution is having None as the default for flags combined
    # with the ability to mark subrecords as required (e.g. for QSDT)
    def pack_subrecord_data(self, record):
        flag_val = getattr(record, self.attr)
        return self.packer(
            flag_val) if flag_val != self._flag_default else None

#------------------------------------------------------------------------------
class MelActivateParents(MelGroup):
    """XAPD/XAPR (Activate Parents) subrecords for REFR records."""
    _ap_flags = TrimmedFlags.from_names('parent_activate_only')

    def __init__(self):
        super().__init__('activate_parents',
            MelUInt8Flags(b'XAPD', 'activate_parent_flags', self._ap_flags),
            MelSorted(MelGroups('activate_parent_refs',
                MelStruct(b'XAPR', ['I', 'f'], (FID, 'ap_reference'),
                    'ap_delay'),
            ), sort_by_attrs='ap_reference'),
        )

#------------------------------------------------------------------------------
class MelActorSounds(MelSorted):
    """Handles the CSDT/CSDI/CSDC subrecord complex used by CREA records in
    TES4/FO3/FNV and NPC_ records in TES5."""
    def __init__(self):
        super().__init__(MelGroups('sounds',
            MelUInt32(b'CSDT', 'type'),
            MelSorted(MelGroups('sound_types',
                MelFid(b'CSDI', 'sound'),
                MelUInt8(b'CSDC', 'chance'),
            ), sort_by_attrs='sound'),
        ), sort_by_attrs='type')

#------------------------------------------------------------------------------
class MelAnimations(MelSorted): ##: case insensitive
    """Handles the common KFFZ (Animations) subrecord."""
    def __init__(self):
        super().__init__(MelStrings(b'KFFZ', 'animations'))

#------------------------------------------------------------------------------
class MelAttx(MelLString):
    """Handles the common ATTX (Activate Text Override) subrecord. Skyrim uses
    an RNAM signature instead."""
    def __init__(self, mel_sig=b'ATTX'):
        super().__init__(mel_sig, 'activate_text_override')

#------------------------------------------------------------------------------
class MelBodyParts(MelSorted):
    """Handles the common NIFZ (Body Parts) subrecord."""
    def __init__(self): ##: case insensitive
        super().__init__(MelStrings(b'NIFZ', 'bodyParts'))

#------------------------------------------------------------------------------
class MelBounds(MelGroup):
    """Wrapper around MelGroup for the common task of defining OBND - Object
    Bounds. Uses MelGroup to avoid merging them when importing."""
    def __init__(self):
        super().__init__('bounds',
            MelStruct(b'OBND', ['6h'], 'boundX1', 'boundY1', 'boundZ1',
                'boundX2', 'boundY2', 'boundZ2'),
        )

#------------------------------------------------------------------------------
class MelCoed(MelOptStruct):
    """Handles the COED (Owner Data) subrecord used for inventory items and
    leveled lists since Skyrim."""
    ##: Needs custom unpacker to look at FormID type of owner.  If owner is an
    # NPC then it is followed by a FormID.  If owner is a faction then it is
    # followed by an signed integer or '=Iif' instead of '=IIf' - see #282
    def __init__(self):
        super().__init__(b'COED', ['I', 'I', 'f'], (FID, 'owner'),
            (FID, 'glob'), 'itemCondition')

#------------------------------------------------------------------------------
class MelColor(MelStruct):
    """Required Color."""
    def __init__(self, color_sig=b'CNAM'):
        super().__init__(color_sig, ['4B'], 'red', 'green', 'blue',
            'unused_alpha')

#------------------------------------------------------------------------------
class MelColorInterpolator(MelArray):
    """Wrapper around MelArray that defines a time interpolator - an array
    of five floats, where each entry in the array describes a point on a curve,
    with 'time' as the X axis and 'red', 'green', 'blue' and 'alpha' as the Y
    axis."""
    def __init__(self, interp_sig, attr):
        super().__init__(attr, MelStruct(interp_sig, ['5f'], 'time', 'red',
            'green', 'blue', 'alpha'))

#------------------------------------------------------------------------------
class MelColorO(MelOptStruct):
    """Optional Color."""
    def __init__(self, color_sig=b'CNAM'):
        super().__init__(color_sig, ['4B'], 'red', 'green', 'blue',
            'unused_alpha')

#------------------------------------------------------------------------------
class MelConditionList(MelGroups):
    """A list of conditions without a counter. Applies to Skyrim and newer
    games. See also MelConditions, which includes a counter for this class."""
    def __init__(self, conditions_attr='conditions'):
        super().__init__(conditions_attr,
            MelGroups('condition_list',
                MelCtdaFo3(suffix_fmt=['2I', 'i'],
                    suffix_elements=['runOn', (FID, 'reference'), 'param3'],
                    old_suffix_fmts={'2I', 'I', ''}),
            ),
            MelString(b'CIS1', 'param_cis1'),
            MelString(b'CIS2', 'param_cis2'),
        )

class MelConditions(MelSequential):
    """Wraps MelSequential to define a condition list with an associated
    counter."""
    def __init__(self):
        super().__init__(
            MelCounter(MelUInt32(b'CITC', 'conditionCount'),
                counts='conditions'),
            MelConditionList(),
        )

#------------------------------------------------------------------------------
class MelCtda(MelUnion):
    """Handles a condition. The difficulty here is that the type of its
    parameters depends on its function index. We handle it by building what
    amounts to a decision tree using MelUnions."""
    # 0 = Unknown/Ignored, 1 = Int, 2 = FormID, 3 = Float
    _param_types = {0: u'4s', 1: u'i', 2: u'I', 3: u'f'}
    # This is technically a lot more complex (the highest three bits also
    # encode the comparison operator), but we only care about use_global, so we
    # can treat the rest as unknown flags and just carry them forward
    _ctda_type_flags = Flags.from_names(
        u'do_or', u'use_aliases', u'use_global', u'use_packa_data',
        u'swap_subject_and_target')

    def __init__(self, ctda_sub_sig=b'CTDA', suffix_fmt=None,
                 suffix_elements=None, old_suffix_fmts=None):
        """Creates a new MelCtda instance with the specified properties.

        :param ctda_sub_sig: The signature of this subrecord. Probably
            b'CTDA'.
        :param suffix_fmt: The struct format string to use, starting after the
            first two parameters.
        :param suffix_elements: The struct elements to use, starting after the
            first two parameters.
        :param old_suffix_fmts: A set of old versions to pass to
            MelTruncatedStruct. Must conform to the same syntax as suffix_fmt.
            May be empty.
        :type old_suffix_fmts: set[str]"""
        if suffix_fmt is None: suffix_fmt = []
        if suffix_elements is None: suffix_elements = []
        if old_suffix_fmts is None: old_suffix_fmts = set()
        from .. import bush
        super(MelCtda, self).__init__({
            # Build a (potentially truncated) struct for each function index
            func_index: self._build_struct(func_data, ctda_sub_sig, suffix_fmt,
                                           suffix_elements, old_suffix_fmts)
            for func_index, func_data
            in bush.game.condition_function_data.items()
        }, decider=PartialLoadDecider(
            # Skip everything up to the function index in one go, we'll be
            # discarding this once we rewind anyways.
            loader=MelStruct(ctda_sub_sig, [u'8s', u'H'], u'ctda_ignored', u'ifunc'),
            decider=AttrValDecider(u'ifunc'),
        ))
        self._ctda_mel = next(iter(self.element_mapping.values())) # type: MelStruct

    # Helper methods - Note that we skip func_data[0]; the first element is
    # the function name, which is only needed for puny human brains
    def _build_struct(self, func_data, ctda_sub_sig, suffix_fmt,
                      suffix_elements, old_suffix_fmts):
        """Builds up a struct from the specified jungle of parameters. Mostly
        inherited from __init__, see there for docs."""
        # The '4s' here can actually be a float or a FormID. We do *not* want
        # to handle this via MelUnion, because the deep nesting is going to
        # cause exponential growth and bring PBash down to a crawl.
        prefix_fmt = [u'B', u'3s', u'4s', u'H', u'2s']
        prefix_elements = [(self._ctda_type_flags, u'operFlag'),
                           u'unused1', u'compValue',
                           u'ifunc', u'unused2']
        # Builds an argument tuple to use for formatting the struct format
        # string from above plus the suffix we got passed in
        fmt_list = [self._param_types[func_param] for func_param in
                    func_data[1:]]
        shared_params = ([ctda_sub_sig, (prefix_fmt + fmt_list + suffix_fmt)] +
                         self._build_params(func_data, prefix_elements,
                                            suffix_elements))
        # Only use MelTruncatedStruct if we have old versions, save the
        # overhead otherwise
        if old_suffix_fmts:
            full_old_versions = {
                u''.join(prefix_fmt + fmt_list + ([f] if f else [])) for f in
                old_suffix_fmts}
            return MelTruncatedStruct(*shared_params,
                                      old_versions=full_old_versions)
        return MelStruct(*shared_params)

    @staticmethod
    def _build_params(func_data, prefix_elements, suffix_elements):
        """Builds a list of struct elements to pass to MelTruncatedStruct."""
        # First, build up a list of the parameter elemnts to use
        func_elements = [
            # 2 == FormID, see PatchGame.condition_function_data
            (FID, u'param%u' % i) if func_param == 2 else u'param%u' % i
            for i, func_param in enumerate(func_data[1:], start=1)]
        # Then, combine the suffix, parameter and suffix elements
        return prefix_elements + func_elements + suffix_elements

    # Nesting workarounds -----------------------------------------------------
    # To avoid having to nest MelUnions too deeply - hurts performance even
    # further (see below) plus grows exponentially
    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        super(MelCtda, self).load_mel(record, ins, sub_type, size_, *debug_strs)
        # See _build_struct comments above for an explanation of this
        record.compValue = struct_unpack(u'fI'[record.operFlag.use_global],
                                         record.compValue)[0]

    def mapFids(self, record, function, save_fids=False):
        super(MelCtda, self).mapFids(record, function, save_fids)
        if record.operFlag.use_global:
            new_comp_val = function(record.compValue)
            if save_fids: record.compValue = new_comp_val

    def dumpData(self, record, out):
        # See _build_struct comments above for an explanation of this
        record.compValue = struct_pack(u'fI'[record.operFlag.use_global],
                                       record.compValue)
        super(MelCtda, self).dumpData(record, out)

    # Some small speed hacks --------------------------------------------------
    # To avoid having to ask 100s of unions to each set their defaults,
    # declare they have fids, etc. Wastes a *lot* of time.
    def hasFids(self, formElements):
        self.fid_elements = list(self.element_mapping.values())
        formElements.add(self)

    def getLoaders(self, loaders):
        loaders[self._ctda_mel.mel_sig] = self

    def getSlotsUsed(self):
        return self.decider_result_attr, *self._ctda_mel.getSlotsUsed()

    def setDefault(self, record):
        next(iter(self.element_mapping.values())).setDefault(record)

class MelCtdaFo3(MelCtda):
    """Version of MelCtda that handles the additional complexities that were
    introduced in FO3 (and present in all games after that):

    1. The 'reference' element is a FormID if runOn is 2, otherwise it is an
    unused uint32. Except for the FNV functions IsFacingUp and IsLeftUp, where
    it is never a FormID. Yup.
    2. The 'GetVATSValue' function is horrible. The type of its second
    parameter depends on the value of the first one. And of course it can be a
    FormID."""
    # Maps param #1 value to the struct format string to use for GetVATSValue's
    # param #2 - missing means unknown/unused, aka 4s
    # Note 18, 19 and 20 were introduced in Skyrim, but since they are not used
    # in FO3 it's no problem to just keep them here
    _vats_param2_fmt = defaultdict(lambda: u'4s', {
        0: u'I', 1: u'I', 2: u'I', 3: u'I', 5: u'i', 6: u'I', 9: u'I',
        10: u'I', 15: u'I', 18: u'I', 19: u'I', 20: u'I'})
    # The param #1 values that indicate param #2 is a FormID
    _vats_param2_fid = {0, 1, 2, 3, 9, 10}

    def __init__(self, suffix_fmt=None, suffix_elements=None,
                 old_suffix_fmts=None):
        super(MelCtdaFo3, self).__init__(suffix_fmt=suffix_fmt,
                                         suffix_elements=suffix_elements,
                                         old_suffix_fmts=old_suffix_fmts)
        from .. import bush
        self._getvatsvalue_ifunc = bush.game.getvatsvalue_index
        self._ignore_ifuncs = ({106, 285} if bush.game.fsName == u'FalloutNV'
                               else set()) # 106 == IsFacingUp, 285 == IsLeftUp

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        super(MelCtdaFo3, self).load_mel(record, ins, sub_type, size_, *debug_strs)
        if record.ifunc == self._getvatsvalue_ifunc:
            record.param2 = struct_unpack(self._vats_param2_fmt[record.param1],
                                          record.param2)[0]

    def mapFids(self, record, function, save_fids=False):
        super(MelCtdaFo3, self).mapFids(record, function, save_fids)
        if record.runOn == 2 and record.ifunc not in self._ignore_ifuncs:
            new_reference = function(record.reference)
            if save_fids: record.reference = new_reference
        if (record.ifunc == self._getvatsvalue_ifunc and
                record.param1 in self._vats_param2_fid):
            new_param2 = function(record.param2)
            if save_fids: record.param2 = new_param2

    def dumpData(self, record, out):
        if record.ifunc == self._getvatsvalue_ifunc:
            record.param2 = struct_pack(self._vats_param2_fmt[record.param1],
                                        record.param2)
        super(MelCtdaFo3, self).dumpData(record, out)

#------------------------------------------------------------------------------
class MelDebrData(MelStruct):
    def __init__(self):
        # Format doesn't matter, struct.Struct('') works! ##: MelStructured
        super().__init__(b'DATA', [], 'percentage', ('modPath', null1),
            'flags')

    @staticmethod
    def _expand_formats(elements, struct_formats):
        return [0] * len(elements)

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        byte_data = ins.read(size_, *debug_strs)
        record.percentage = unpack_byte(ins, byte_data[0:1])[0]
        record.modPath = byte_data[1:-2]
        if byte_data[-2] != null1:
            raise ModError(ins.inName, f'Unexpected subrecord: {debug_strs}')
        record.flags = struct_unpack('B', byte_data[-1])[0]

    def pack_subrecord_data(self, record):
        return b''.join(
            [struct_pack('B', record.percentage), record.modPath, null1,
             struct_pack('B', record.flags)])

#------------------------------------------------------------------------------
class MelDecalData(MelOptStruct):
    _decal_data_flags = TrimmedFlags.from_names(
        'parallax',
        'alphaBlending',
        'alphaTesting',
        'noSubtextures', # Skyrim+, will just be ignored for earlier games
    )

    def __init__(self):
        super().__init__(b'DODT', ['7f', 'B', 'B', '2s', '3B', 's'],
            'minWidth', 'maxWidth', 'minHeight', 'maxHeight', 'depth',
            'shininess', 'parallaxScale', 'parallaxPasses',
            (self._decal_data_flags, 'decalFlags'), 'unusedDecal1',
            'redDecal', 'greenDecal', 'blueDecal', 'unusedDecal2')

#------------------------------------------------------------------------------
class MelDescription(MelLString):
    """Handles a description (DESC) subrecord."""
    def __init__(self, desc_attr='description'):
        super().__init__(b'DESC', desc_attr)

#------------------------------------------------------------------------------
class MelEdid(MelString):
    """Handles an Editor ID (EDID) subrecord."""
    def __init__(self):
        super().__init__(b'EDID', 'eid')

#------------------------------------------------------------------------------
class MelEnableParent(MelOptStruct):
    """Enable Parent struct for a reference record (REFR, ACHR, etc.)."""
    # The pop_in flag doesn't technically exist for all XESP subrecords, but it
    # will just be ignored for those where it doesn't exist, so no problem.
    _parent_flags = Flags.from_names('opposite_parent', 'pop_in')

    def __init__(self):
        super().__init__(b'XESP', ['I', 'B', '3s'], (FID, 'ep_reference'),
            (self._parent_flags, 'parent_flags'), 'xesp_unused')

#------------------------------------------------------------------------------
class MelEnchantment(MelFid):
    """Represents the common enchantment/object effect subrecord."""
    def __init__(self, ench_sig=b'EITM'):
        super().__init__(ench_sig, 'enchantment')

#------------------------------------------------------------------------------
class MelFactionRanks(MelSorted):
    """Handles the FACT RNAM/MNAM/FNAM/INAM subrecords."""
    def __init__(self):
        super().__init__(MelGroups('ranks',
            MelSInt32(b'RNAM', 'rank_level'),
            MelLString(b'MNAM', 'male_title'),
            MelLString(b'FNAM', 'female_title'),
            MelString(b'INAM', 'insignia_path'),
        ), sort_by_attrs='rank_level')

#------------------------------------------------------------------------------
class MelFactions(MelSorted):
    """Handles the common SNAM (Factions) subrecord."""
    def __init__(self):
        super().__init__(MelGroups('factions',
            MelStruct(b'SNAM', ['I', 'B', '3s'], (FID, 'faction'), 'rank',
                ('unused1', b'ODB')),
        ), sort_by_attrs='faction')

#------------------------------------------------------------------------------
class MelFull(MelLString):
    """Handles a name (FULL) subrecord."""
    def __init__(self):
        super().__init__(b'FULL', 'full')

#------------------------------------------------------------------------------
class MelIcons(MelSequential):
    """Handles icon subrecords. Defaults to ICON and MICO, with attribute names
    'iconPath' and 'smallIconPath', since that's most common."""
    def __init__(self, icon_attr='iconPath', mico_attr='smallIconPath',
            icon_sig=b'ICON', mico_sig=b'MICO'):
        """Creates a new MelIcons with the specified attributes.

        :param icon_attr: The attribute to use for the ICON subrecord. If
            falsy, this means 'do not include an ICON subrecord'.
        :param mico_attr: The attribute to use for the MICO subrecord. If
            falsy, this means 'do not include a MICO subrecord'."""
        final_elements = []
        if icon_attr: final_elements.append(MelString(icon_sig, icon_attr))
        if mico_attr: final_elements.append(MelString(mico_sig, mico_attr))
        super().__init__(*final_elements)

class MelIcons2(MelIcons):
    """Handles ICO2 and MIC2 subrecords. Defaults to attribute names
    'femaleIconPath' and 'femaleSmallIconPath', since that's most common."""
    def __init__(self, ico2_attr='femaleIconPath',
            mic2_attr='femaleSmallIconPath'):
        super().__init__(icon_attr=ico2_attr, mico_attr=mic2_attr,
            icon_sig=b'ICO2', mico_sig=b'MIC2')

class MelIcon(MelIcons):
    """Handles a standalone ICON subrecord, i.e. without any MICO subrecord."""
    def __init__(self, icon_attr='iconPath'):
        super().__init__(icon_attr=icon_attr, mico_attr='')

class MelIco2(MelIcons2):
    """Handles a standalone ICO2 subrecord, i.e. without any MIC2 subrecord."""
    def __init__(self, ico2_attr):
        super().__init__(ico2_attr=ico2_attr, mic2_attr='')

#------------------------------------------------------------------------------
class MelInteractionKeyword(MelFid):
    """Handles the KNAM (Interaction Keyword) subrecord of ACTI records."""
    def __init__(self):
        super().__init__(b'KNAM', 'interaction_keyword')

#------------------------------------------------------------------------------
class MelKeywords(MelSequential):
    """Wraps MelSequential for the common task of defining a list of keywords
    and a corresponding counter."""
    def __init__(self):
        super().__init__(
            MelCounter(MelUInt32(b'KSIZ', 'keyword_count'), counts='keywords'),
            MelSorted(MelSimpleArray('keywords', MelFid(b'KWDA'))),
        )

#------------------------------------------------------------------------------
class MelLscrLocations(MelSorted):
    """Handles the LSCR subrecord LNAM (Locations)."""
    def __init__(self):
        super().__init__(MelGroups('locations',
            MelStruct(b'LNAM', ['2I', '2h'], (FID, 'direct'),
                (FID, 'indirect'), 'gridy', 'gridx'),
        ), sort_by_attrs=('direct', 'indirect', 'gridy', 'gridx'))

#------------------------------------------------------------------------------
class MelMapMarker(MelGroup):
    """Map marker struct for a reference record (REFR, ACHR, etc.). Also
    supports the WMI1 subrecord from FNV."""
    # Same idea as above - show_all_hidden is FO3+, but that's no problem.
    _marker_flags = Flags.from_names('visible', 'can_travel_to',
                                     'show_all_hidden')

    def __init__(self, with_reputation=False):
        group_elems = [
            MelBase(b'XMRK', 'marker_data'),
            MelUInt8Flags(b'FNAM', 'marker_flags', self._marker_flags),
            MelFull(),
            MelOptStruct(b'TNAM', ['B', 's'], 'marker_type', 'unused1'),
        ]
        if with_reputation:
            group_elems.append(MelFid(b'WMI1', 'marker_reputation'))
        super().__init__('map_marker', *group_elems)

#------------------------------------------------------------------------------
class MelMdob(MelFid):
    """Represents the common Menu Display Object subrecord."""
    def __init__(self):
        super().__init__(b'MDOB', 'menu_display_object')

#------------------------------------------------------------------------------
class MelMODS(MelBase):
    """MODS/MO2S/etc/DMDS subrecord"""
    _fid_element = MelFid(null1) # dummy MelFid instance to use its loader

    def hasFids(self,formElements):
        formElements.add(self)

    def setDefault(self,record):
        setattr(record, self.attr, None)

    def load_mel(self, record, ins, sub_type, size_, *debug_strs,
                 __unpacker=int_unpacker, __load_fid=_fid_element.load_bytes):
        insUnpack = ins.unpack
        insRead32 = ins.readString32
        count, = insUnpack(__unpacker, 4, *debug_strs)
        mods_data = []
        dataAppend = mods_data.append
        for x in range(count):
            string = insRead32(*debug_strs)
            int_fid = __load_fid(ins, 4)
            index, = insUnpack(__unpacker, 4, *debug_strs)
            dataAppend((string, int_fid, index))
        setattr(record, self.attr, mods_data)

    def pack_subrecord_data(self, record, *, __packer=structs_cache['I'].pack,
                            __fid_packer=_fid_element.packer):
        mods_data = getattr(record, self.attr)
        if mods_data is not None:
            # Sort by 3D Name and 3D Index
            mods_data.sort(key=lambda e: (e[0], e[2]))
            return b''.join([__packer(len(mods_data)), *(chain(*(
                [__packer(len(string)), encode(string), __fid_packer(int_fid),
                 __packer(index)] for (string, int_fid, index) in
            mods_data)))])

    def mapFids(self, record, function, save_fids=False):
        attr = self.attr
        mods_data = getattr(record, attr)
        if mods_data is not None:
            mods_data = [(string,function(fid),index) for (string,fid,index)
                         in mods_data]
            if save_fids: setattr(record, attr, mods_data)

#------------------------------------------------------------------------------
class MelOwnership(MelGroup):
    """Handles XOWN, XRNK for cells and cell children."""

    def __init__(self, attr='ownership'):
        MelGroup.__init__(self, attr,
            MelFid(b'XOWN', 'owner'),
            MelSInt32(b'XRNK', 'rank'),
        )

    def dumpData(self,record,out): ##: use pack_subrecord_data ?
        if record.ownership and record.ownership.owner:
            MelGroup.dumpData(self,record,out)

#------------------------------------------------------------------------------
##: This is a strange fusion of MelLists, MelStruct and MelTruncatedStruct
# because one of the attrs is a flags field and in Skyrim it's truncated too
class MelRaceData(MelTruncatedStruct):
    """Pack RACE skills and skill boosts as a single attribute."""

    def __init__(self, sub_sig, sub_fmt, *elements, **kwargs):
        if 'old_versions' not in kwargs:
            kwargs['old_versions'] = set() # set default to avoid errors
        super().__init__(sub_sig, sub_fmt, *elements, **kwargs)

    @staticmethod
    def _expand_formats(elements, struct_formats):
        expanded_fmts = []
        for f in struct_formats:
            if f == '14b':
                expanded_fmts.append(0)
            elif f[-1] != 's':
                expanded_fmts.extend([f[-1]] * int(f[:-1] or 1))
            else:
                expanded_fmts.append(int(f[:-1] or 1))
        return expanded_fmts

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        try:
            target_unpacker = self._all_unpackers[size_]
        except KeyError:
            raise ModSizeError(ins.inName, debug_strs,
                               tuple(self._all_unpackers), size_)
        unpacked = ins.unpack(target_unpacker, size_, *debug_strs)
        unpacked = self._pre_process_unpacked(unpacked)
        record.skills = unpacked[:14]
        for attr, value, action in zip(self.attrs[1:], unpacked[14:],
                                        self.actions[1:]):
            setattr(record, attr,
                    action(value) if action is not None else value)

    def pack_subrecord_data(self, record):
        values = list(record.skills)
        values.extend(
            action(value).dump() if action is not None else value
            for value, action in zip(
                (getattr(record, a) for a in self.attrs[1:]),
                self.actions[1:]))
        return self._packer(*values)

#------------------------------------------------------------------------------
class MelRaceParts(MelNull):
    """Handles a subrecord array, where each subrecord is introduced by an
    INDX subrecord, which determines the meaning of the subrecord. The
    resulting attributes are set directly on the record."""
    def __init__(self, indx_to_attr: dict[int, str], group_loaders):
        """Creates a new MelRaceParts element with the specified INDX mapping
        and group loaders.

        :param indx_to_attr: A mapping from the INDX values to the final
            record attributes that will be used for the subsequent
            subrecords.
        :param group_loaders: A callable that takes the INDX value and
            returns an iterable with one or more MelBase-derived subrecord
            loaders. These will be loaded and dumped directly after each
            INDX."""
        self._last_indx = None # used during loading
        self._indx_to_attr = indx_to_attr
        # Create loaders for use at runtime
        self._indx_to_loader: dict[int, MelBase] = {
            part_indx: MelGroup(part_attr, *group_loaders(part_indx))
            for part_indx, part_attr in indx_to_attr.items()
        }
        self._possible_sigs = {s for element
                               in self._indx_to_loader.values()
                               for s in element.signatures}

    def getLoaders(self, loaders):
        temp_loaders = {}
        for element in self._indx_to_loader.values():
            element.getLoaders(temp_loaders)
        for signature in temp_loaders:
            loaders[signature] = self

    def getSlotsUsed(self):
        return tuple(self._indx_to_attr.values())

    def setDefault(self, record):
        for element in self._indx_to_loader.values():
            element.setDefault(record)

    def load_mel(self, record, ins, sub_type, size_, *debug_strs,
                 __unpacker=int_unpacker):
        if sub_type == b'INDX':
            self._last_indx = ins.unpack(__unpacker, size_, *debug_strs)[0]
        else:
            self._indx_to_loader[self._last_indx].load_mel(record, ins,
                sub_type, size_, *debug_strs)

    def dumpData(self, record, out):
        # Note that we have to dump out the attributes sorted by the INDX value
        for part_indx, part_attr in dict_sort(self._indx_to_attr):
            if hasattr(record, part_attr): # only dump present parts
                MelUInt32(b'INDX', 'UNUSED').packSub(out,
                    struct_pack('=I', part_indx))
                self._indx_to_loader[part_indx].dumpData(record, out)

    @property
    def signatures(self):
        return self._possible_sigs

#------------------------------------------------------------------------------
class MelRaceVoices(MelStruct):
    """Set voices to zero, if equal race fid. If both are zero, then skip
    dumping."""
    def pack_subrecord_data(self, record):
        if record.maleVoice == record.fid: record.maleVoice = 0
        if record.femaleVoice == record.fid: record.femaleVoice = 0
        if (record.maleVoice, record.femaleVoice) != (0, 0):
            return super().pack_subrecord_data(record)
        return None

#------------------------------------------------------------------------------
class MelRef3D(MelOptStruct):
    """3D position and rotation for a reference record (REFR, ACHR, etc.)."""
    def __init__(self):
        super().__init__(b'DATA', ['6f'], 'ref_pos_x', 'ref_pos_y',
            'ref_pos_z', 'ref_rot_x', 'ref_rot_y', 'ref_rot_z')

#------------------------------------------------------------------------------
class MelReferences(MelGroups):
    """Handles mixed sets of SCRO and SCRV for scripts, quests, etc."""
    def __init__(self):
        super().__init__('references', MelUnion({
            b'SCRO': MelFid(b'SCRO', 'reference'),
            b'SCRV': MelUInt32(b'SCRV', 'reference'),
        }))

#------------------------------------------------------------------------------
class MelReflectedRefractedBy(MelSorted):
    """Reflected/Refracted By for a reference record (REFR, ACHR, etc.)."""
    _watertypeFlags = Flags.from_names('reflection', 'refraction')

    def __init__(self):
        super().__init__(MelGroups('reflectedRefractedBy',
            MelStruct(b'XPWR', ['2I'], (FID, 'waterReference'),
                (self._watertypeFlags, 'waterFlags')),
        ), sort_by_attrs='waterReference')

#------------------------------------------------------------------------------
class MelRefScale(MelFloat):
    """Scale for a reference record (REFR, ACHR, etc.)."""
    def __init__(self): # default was 1.0
        super().__init__(b'XSCL', 'ref_scale')

#------------------------------------------------------------------------------
class MelRegions(MelSorted):
    """Handles the CELL subrecord XCLR (Regions)."""
    def __init__(self):
        super().__init__(MelSimpleArray('regions', MelFid(b'XCLR')))

#------------------------------------------------------------------------------
class MelRegnEntrySubrecord(MelUnion):
    """Wrapper around MelUnion to correctly read/write REGN entry data.
    Skips loading and dumping if entryType != entry_type_val.

    entry_type_val meanings:
      - 2: Objects
      - 3: Weather
      - 4: Map
      - 5: Land
      - 6: Grass
      - 7: Sound
      - 8: Imposter (FNV only)"""
    def __init__(self, entry_type_val: int, element):
        super().__init__({
            entry_type_val: element,
        }, decider=AttrValDecider('entryType'),
            fallback=MelNull(b'NULL')) # ignore

#------------------------------------------------------------------------------
class MelRelations(MelSorted):
    """Handles the common XNAM (Relations) subrecord. Group combat reaction
    (GCR) can be excluded (i.e. in Oblivion)."""
    def __init__(self, with_gcr=True):
        rel_fmt = ['I', 'i']
        rel_elements = [(FID, 'faction'), 'mod']
        if with_gcr:
            rel_fmt.append('I')
            rel_elements.append('group_combat_reaction')
        super().__init__(MelGroups('relations',
            MelStruct(b'XNAM', rel_fmt, *rel_elements),
        ), sort_by_attrs='faction')

#------------------------------------------------------------------------------
class MelScript(MelFid):
    """Represents the common script subrecord in TES4/FO3/FNV."""
    def __init__(self):
        super().__init__(b'SCRI', 'script_fid')

#------------------------------------------------------------------------------
class MelScriptVars(MelSorted):
    """Handles SLSD and SCVR combos defining script variables."""
    def __init__(self):
        super().__init__(MelGroups('script_vars',
            MelStruct(b'SLSD', ['I', '12s', 'B', '7s'], 'var_index', 'unused1',
                'var_type', 'unused2'),
            MelString(b'SCVR', 'var_name'),
        ), sort_by_attrs='var_index')

#------------------------------------------------------------------------------
class MelSkipInterior(MelUnion):
    """Union that skips dumping if we're in an interior."""
    def __init__(self, element):
        super().__init__({
            True: MelReadOnly(element),
            False: element,
        }, decider=FlagDecider('flags', ['isInterior']))

#------------------------------------------------------------------------------
class MelSoundActivation(MelFid):
    """Handles the VNAM (Sound - Activation) subrecord in ACTI records."""
    def __init__(self):
        super().__init__(b'VNAM', 'soundActivation')

#------------------------------------------------------------------------------
class MelSoundDrop(MelFid):
    """Handles the common ZNAM (Drop Sound) subrecord."""
    def __init__(self):
        super().__init__(b'ZNAM', 'dropSound')

#------------------------------------------------------------------------------
class MelSoundLooping(MelFid):
    """Handles the common SNAM (Sound - Looping) subrecord."""
    def __init__(self):
        super().__init__(b'SNAM', 'soundLooping')

#------------------------------------------------------------------------------
class MelSoundPickup(MelFid):
    """Handles the common YNAM (Pickup Sound) subrecord."""
    def __init__(self):
        super().__init__(b'YNAM', 'pickupSound')

#------------------------------------------------------------------------------
class MelSpells(MelSorted):
    """Handles the common SPLO subrecord."""
    def __init__(self):
        super().__init__(MelFids('spells', MelFid(b'SPLO')))

#------------------------------------------------------------------------------
# xEdit calls this 'time interpolator', but that name doesn't really make sense
# Both this class and the color interpolator above interpolate over time
class MelValueInterpolator(MelArray):
    """Wrapper around MelArray that defines a value interpolator - an array
    of two floats, where each entry in the array describes a point on a curve,
    with 'time' as the X axis and 'value' as the Y axis."""
    def __init__(self, interp_sig, attr):
        super().__init__(attr, MelStruct(interp_sig, ['2f'], 'time', 'value'))

#------------------------------------------------------------------------------
class MelValueWeight(MelStruct):
    """Handles a common variant of the DATA subrecord that consists of one
    integer (the value of an object) and one float (the weight of an
    object)."""
    def __init__(self):
        super().__init__(b'DATA', ['I', 'f'], 'value', 'weight')

#------------------------------------------------------------------------------
class MelWaterType(MelFid):
    """Handles the common WNAM (Water Type) subrecord."""
    def __init__(self):
        super().__init__(b'WNAM', 'water_type')

#------------------------------------------------------------------------------
class MelWeatherTypes(MelSorted):
    """Handles the CLMT subrecord WLST (Weather Types)."""
    def __init__(self, with_global=True):
        weather_fmt = ['I', 'i']
        weather_elements = [(FID, 'weather'), 'chance']
        if with_global:
            weather_fmt.append('I')
            weather_elements.append((FID, 'global'))
        super().__init__(MelArray('weather_types',
            MelStruct(b'WLST', weather_fmt, *weather_elements),
        ), sort_by_attrs='weather')

#------------------------------------------------------------------------------
class MelWorldBounds(MelSequential):
    """Worldspace (WRLD) bounds."""
    def __init__(self):
        super().__init__(
            MelStruct(b'NAM0', ['2f'], 'object_bounds_min_x',
                'object_bounds_min_y'),
            MelStruct(b'NAM9', ['2f'], 'object_bounds_max_x',
                'object_bounds_max_y'),
        )

#------------------------------------------------------------------------------
class MelWthrColors(MelStruct):
    """Used in WTHR for PNAM and NAM0 for all games but FNV."""
    def __init__(self, wthr_sub_sig):
        super().__init__(wthr_sub_sig, ['3B', 's', '3B', 's', '3B', 's', '3B',
                                        's'], 'riseRed', 'riseGreen',
            'riseBlue', 'unused1', 'dayRed', 'dayGreen', 'dayBlue', 'unused2',
            'setRed', 'setGreen', 'setBlue', 'unused3', 'nightRed',
            'nightGreen', 'nightBlue', 'unused4')

#------------------------------------------------------------------------------
class MelXlod(MelOptStruct):
    """Distant LOD Data."""
    def __init__(self):
        super().__init__(b'XLOD', ['3f'], 'lod1', 'lod2', 'lod3')

#------------------------------------------------------------------------------
class _SpellFlags(Flags):
    """For SpellFlags, immuneToSilence activates bits 1 AND 3."""
    __slots__ = []

    def __setitem__(self, index, value):
        setter = Flags.__setitem__
        setter(self, index, value)
        if index == 1:
            setter(self, 3, value)

SpellFlags = _SpellFlags.from_names('noAutoCalc','immuneToSilence',
    'startSpell', None, 'ignoreLOS', 'scriptEffectAlwaysApplies',
    'disallowAbsorbReflect', 'touchExplodesWOTarget')
