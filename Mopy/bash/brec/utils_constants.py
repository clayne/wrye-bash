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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Houses the parts of brec that didn't fit anywhere else or were needed by
almost all other parts of brec."""
from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from itertools import chain

from .. import bolt, bush
from ..bolt import Flags, attrgetter_cache, cstrip, decoder, flag, \
    structs_cache, FName, fast_cached_property
from ..exception import StateError

# no local imports, imported everywhere in brec

# Form ids --------------------------------------------------------------------
class FormId:
    """Immutable class wrapping an (integer) plugin form ID. These must be
    instantiated in a ModReader context which injects the master table to
    use for the long fid conversions. Base class performs no conversion."""

    def __init__(self, int_val):
        if not isinstance(int_val, int):
            ##: re add : {int_val!r} when setDefault is gone - huge performance
            # impact as it run for all _Tes4Fid and blows - repr is expensive!
            raise TypeError('Only int accepted in FormId')
        self.short_fid = int_val

    # factories
    __master_formid_type: dict[FName, type] = {} # cache a formid type per mod
    # cache a formid type per masters list and Overlay flag state
    _form_id_classes: dict[tuple[tuple[FName, ...], bool], type] = {}
    @classmethod
    def from_tuple(cls, fid_tuple):
        """Return a FormId (subclass) instance with a given long id - does not
        implement mod_dex which means use sparingly - mostly used for
        parsers (csvs) and through game.master_fid."""
        try:
            return cls.__master_formid_type[fid_tuple[0]](fid_tuple[1])
        except KeyError:
            class __FormId(cls):
                @fast_cached_property
                def long_fid(self):
                    return fid_tuple[0], self.short_fid
                @property
                def mod_dex(self):
                    """short_fid corresponds to object_dex in this case."""
                    raise StateError(f'mod_dex undefined for {self} built '
                                     f'from tuple')
            cls.__master_formid_type[fid_tuple[0]] = __FormId
            return __FormId(fid_tuple[1])

    @classmethod
    def from_object_id(cls, modIndex, objectIndex):
        """Return a FormId instance with a shortid generated by a mod and
        object index - use sparingly!"""
        return cls(objectIndex | (modIndex << 24))

    @staticmethod
    def from_masters(augmented_masters: tuple[FName, ...],
            in_overlay_plugin: bool):
        """Return a subclass of FormId using the specified masters for long fid
        conversions."""
        try:
            form_id_type = FormId._form_id_classes[(augmented_masters,
                                                    in_overlay_plugin)]
        except KeyError:
            if in_overlay_plugin:
                overlay_threshold = len(augmented_masters) - 1
                class _FormID(FormId):
                    @fast_cached_property
                    def long_fid(self, *, __masters=augmented_masters):
                        try:
                            if self.mod_dex >= overlay_threshold:
                                # Overlay plugins can't have new records (or
                                # HITMEs), those get injected into the first
                                # master instead
                                return __masters[0], self.short_fid & 0xFFFFFF
                            return __masters[self.mod_dex], \
                                   self.short_fid & 0xFFFFFF
                        except IndexError:
                            # Clamp HITMEs to the plugin's own address space
                            return __masters[-1], self.short_fid & 0xFFFFFF
            else:
                class _FormID(FormId):
                    @fast_cached_property
                    def long_fid(self, *, __masters=augmented_masters):
                        try:
                            return __masters[self.mod_dex], \
                                   self.short_fid & 0xFFFFFF
                        except IndexError:
                            # Clamp HITMEs to the plugin's own address space
                            return __masters[-1], self.short_fid & 0xFFFFFF
            form_id_type = FormId._form_id_classes[augmented_masters] = _FormID
        return form_id_type

    @fast_cached_property
    def long_fid(self):
        """Don't map by default."""
        return self.short_fid

    @property # ~0.006s on a 60s BP - no need to cache
    def object_dex(self):
        """Always recoverable from short fid."""
        return self.short_fid & 0x00FFFFFF

    @property
    def mod_dex(self):
        """Always recoverable from short fid - but see from_tuple."""
        return self.short_fid >> 24

    @property # ~0.03s on a 60s BP - no need to cache
    def mod_fn(self):
        """Return the mod id - will raise if long_fid is not a tuple."""
        try:
            return self.long_fid[0]
        except TypeError as e:
            raise StateError(f'{self!r} not in long format') from e

    def is_null(self):
        """Return True if we are a round 0."""
        # Use object_dex instead of short_fid here since 01000000 is also NULL
        return self.object_dex == 0

    # Hash and comparisons
    def __hash__(self):
        return hash(self.long_fid)

    def __eq__(self, other):
        with suppress(AttributeError):
            return self.long_fid == other.long_fid
        if other is None:
            return False
        elif isinstance(self.long_fid, type(other)):
            return self.long_fid == other
        return NotImplemented

    def __ne__(self, other):
        with suppress(AttributeError):
            return self.long_fid != other.long_fid
        if other is None:
            return True
        elif isinstance(self.long_fid, type(other)):
            return self.long_fid != other
        return NotImplemented

    def __lt__(self, other):
        with suppress(TypeError):
            # If we're in a write context, compare FormIds properly
            return short_mapper(self) < short_mapper(other)
        # Otherwise, use alphanumeric order
        ##: This is a hack - rewrite _AMerger to not sort and absorb all
        # mergers (see #497). Same with all the other compare dunders
        with suppress(AttributeError):
            return self.long_fid < other.long_fid
        if isinstance(self.long_fid, type(other)):
            return self.long_fid < other
        return NotImplemented

    def __ge__(self, other):
        with suppress(TypeError):
            return short_mapper(self) >= short_mapper(other)
        with suppress(AttributeError):
            return self.long_fid >= other.long_fid
        if isinstance(self.long_fid, type(other)):
            return self.long_fid >= other
        return NotImplemented

    def __gt__(self, other):
        with suppress(TypeError):
            return short_mapper(self) > short_mapper(other)
        with suppress(AttributeError):
            return self.long_fid > other.long_fid
        if isinstance(self.long_fid, type(other)):
            return self.long_fid > other
        return NotImplemented

    def __le__(self, other):
        with suppress(TypeError):
            return short_mapper(self) <= short_mapper(other)
        with suppress(AttributeError):
            return self.long_fid <= other.long_fid
        if isinstance(self.long_fid, type(other)):
            return self.long_fid <= other
        return NotImplemented

    # avoid setstate/getstate round trip
    def __deepcopy__(self, memodict={}):
        return self # immutable

    def __copy__(self):
        return self # immutable

    def __getstate__(self):
        raise NotImplementedError("You can't pickle a FormId")

    def __str__(self):
        if isinstance(self.long_fid, tuple):
            return f'({self.long_fid[0]}, {self.long_fid[1]:06X})'
        else:
            return f'{self.long_fid:08X}'

    def __repr__(self):
        return f'{type(self).__name__}({self})'

    # Action API --------------------------------------------------------------
    def dump(self):
        return short_mapper(self)

class _NoneFid:
    """Special FormId value of NONE, which sorts last always.  Used in FO4, and
    internally for sorted lists which don't have a FormId but need to sort last.

    NOTE: Not derived from FormId, since we want this to blow if FormId's other
    methods are called on this.
    """
    def __init__(self):
        pass

    def __str__(self) -> str:
        return 'NONE'

    def __repr__(self) -> str:
        return 'FormId(NONE)'

    def __lt__(self, other: FormId | _NoneFid) -> bool:
        if isinstance(other, (FormId, _NoneFid)):
            return False
        return NotImplemented

    def __le__(self, other: FormId | _NoneFid) -> bool:
        return not self > other

    def __gt__(self, other: FormId | _NoneFid) -> bool:
        if isinstance(other, FormId):
            return True
        elif isinstance(other, _NoneFid):
            return False
        return NotImplemented

    def __ge__(self, other: FormId | _NoneFid) -> bool:
        return not self < other

    def __eq__(self, other: FormId | _NoneFid) -> bool:
        if isinstance(other, FormId):
            return False
        elif isinstance(other, _NoneFid):
            return True
        return NotImplemented

    def __ne__(self, other: FormId | _NoneFid) -> bool:
        return not self == other

    def dump(self) -> int:
        return 0xFFFFFFFF

class _Tes4Fid(FormId):
    """The special formid of the plugin header record - aka 0. Also used
    as a MelStruct default and when we set the form id to "zero" in some
    edge cases."""
    def dump(self): return 0

    @fast_cached_property
    def long_fid(self):
        return bush.game.master_fid(0).long_fid

# cache an instance of Tes4 and export that to the rest of Bash
ZERO_FID = _Tes4Fid(0)
NONE_FID = _NoneFid()

# Global FormId class used to wrap all formids of currently loading mod. It
# must be set by the mod reader context manager based on the currently loading
# plugin
FORM_ID: type[FormId] | None = None

# Global short mapper function. Set by the plugin output context manager.
# Maps the fids based on the masters of the currently dumped plugin
short_mapper: Callable | None = None
short_mapper_no_engine: Callable | None = None

# Used by Mel classes to wrap fid elements.
FID = lambda x: FORM_ID(x)

class _DummyFid(_Tes4Fid):
    """Used by setDefault (yak) - will blow on dump, make sure you replace
    it with a proper FormId."""
    def dump(self):
        raise NotImplementedError('Dumping a dummy fid')
DUMMY_FID = _DummyFid(0)

# Random stuff ----------------------------------------------------------------
int_unpacker = structs_cache['I'].unpack

class FixedString(str):
    """An action for MelStructs that will decode and encode a fixed-length
    string. Note that you do not need to specify defaults when using this."""
    __slots__ = ('_str_length',)
    _str_encoding = bolt.pluginEncoding

    def __new__(cls, str_length, target_str: str | bytes = ''):
        if isinstance(target_str, str):
            decoded_str = target_str
        else:
            decoded_str = '\n'.join(
                decoder(x, cls._str_encoding, avoidEncodings=('utf8', 'utf-8'))
                for x in cstrip(target_str).split(b'\n'))
        new_str = super(FixedString, cls).__new__(cls, decoded_str)
        new_str._str_length = str_length
        return new_str

    def __call__(self, new_str):
        # 0 is the default, so replace it with whatever we currently have
        return self.__class__(self._str_length, new_str or str(self))

    def __deepcopy__(self, memodict={}):
        return self # immutable

    def __copy__(self):
        return self # immutable

    def dump(self):
        return bolt.encode_complex_string(self, max_size=self._str_length,
                                          min_size=self._str_length)

class AutoFixedString(FixedString):
    """Variant of FixedString that uses chardet to detect encodings."""
    _str_encoding = None

# Common flags ----------------------------------------------------------------
class AMgefFlags(Flags):
    """Base class for MGEF data flags shared by all games."""
    hostile: bool = flag(0)
    recover: bool = flag(1)
    detrimental: bool = flag(2)
    no_hit_effect: bool = flag(27)

class AMgefFlagsTes4(AMgefFlags):
    """Base class for MGEF data flags from Oblivion to FO3."""
    mgef_self: bool = flag(4)
    mgef_touch: bool = flag(5)
    mgef_target: bool = flag(6)
    no_duration: bool = flag(7)
    no_magnitude: bool = flag(8)
    no_area: bool = flag(9)
    fx_persist: bool = flag(10)
    use_skill: bool = flag(19)
    use_attribute: bool = flag(20)
    spray_projectile_type: bool = flag(25)
    bolt_projectile_type: bool = flag(26)

    @property
    def fog_projectile_type(self) -> bool:
        """If flags 25 and 26 are set, specifies fog_projectile_type."""
        mask = 0b00000110000000000000000000000000
        return (self._field & mask) == mask

    @fog_projectile_type.setter
    def fog_projectile_type(self, new_fpt: bool) -> None:
        mask = 0b00000110000000000000000000000000
        new_bits = mask if new_fpt else 0
        self._field = (self._field & ~mask) | new_bits

class EnableParentFlags(Flags):
    """Implements the enable parent flags shared by XESP, ACEP and LCEP."""
    opposite_parent: bool
    # The pop_in flag doesn't technically exist for all XESP subrecords, but it
    # will just be ignored for those where it doesn't exist, so no problem.
    pop_in: bool

class MgefFlags(AMgefFlags):
    """Implements the MGEF data flags used since Skyrim."""
    snap_to_navmesh: bool = flag(3)
    no_hit_event: bool = flag(4)
    dispel_with_keywords: bool = flag(8)
    no_duration: bool = flag(9)
    no_magnitude: bool = flag(10)
    no_area: bool = flag(11)
    fx_persist: bool = flag(12)
    gory_visuals: bool = flag(14)
    hide_in_ui: bool = flag(15)
    no_recast: bool = flag(17)
    power_affects_magnitude: bool = flag(21)
    power_affects_duration: bool = flag(22)
    painless: bool = flag(26)
    no_death_dispel: bool = flag(28)

class PackGeneralFlags(Flags):
    """Implements the new version of the general PACK/PKDT flags (Skyrim and
    newer)."""
    offers_services: bool = flag(0)
    must_complete: bool = flag(2)
    maintain_speed_at_goal: bool = flag(3)
    unlock_doors_at_package_start: bool = flag(6)
    unlock_doors_at_package_end: bool = flag(7)
    continue_if_pc_near: bool = flag(9)
    once_per_day: bool = flag(10)
    preferred_speed: bool = flag(13)
    always_sneak: bool = flag(17)
    allow_swimming: bool = flag(18)
    ignore_combat: bool = flag(20)
    weapons_unequipped: bool = flag(21)
    weapon_drawn: bool = flag(23)
    no_combat_alert: bool = flag(27)
    wear_sleep_outfit: bool = flag(29)

class PackGeneralOldFlags(Flags):
    """Implements the old version of the general PACK/PKDT flags (FNV and
    older)."""
    offers_services: bool = flag(0)
    must_reach_location: bool = flag(1)
    must_complete: bool = flag(2)
    lock_at_start: bool = flag(3)
    lock_at_end: bool = flag(4)
    lock_at_location: bool = flag(5)
    unlock_at_start: bool = flag(6)
    unlock_at_end: bool = flag(7)
    unlock_at_location: bool = flag(8)
    continue_if_pc_near: bool = flag(9)
    once_per_day: bool = flag(10)
    skip_fallout_behavior: bool = flag(12)
    always_run: bool = flag(13)
    always_sneak: bool = flag(17)
    allow_swimming: bool = flag(18)
    allow_falls: bool = flag(19)
    unequip_armor: bool = flag(20)
    unequip_weapons: bool = flag(21)
    defensive_combat: bool = flag(22)
    use_horse: bool = flag(23)
    no_idle_anims: bool = flag(24)

class PackInterruptFlags(Flags):
    """Implements the since-Skyrim interrupt PACK/PKDT flags. Adapted from the
    'Fallout Behavior Flags' in FO3/FNV."""
    hellos_to_player: bool = flag(0)
    random_conversations: bool = flag(1)
    observe_combat_behavior: bool = flag(2)
    greet_corpse_behavior: bool = flag(3)
    reaction_to_player_actions: bool = flag(4)
    friendly_fire_comments: bool = flag(5)
    aggro_radius_behavior: bool = flag(6)
    allow_idle_chatter: bool = flag(7)
    world_interactions: bool = flag(9)

class TemplateFlags(Flags):
    """NPC_ (and CREA, in FO3) template flags, present since FO3."""
    use_traits: bool
    use_stats: bool
    use_factions: bool
    use_spell_list: bool
    use_ai_data: bool
    use_ai_packages: bool
    use_model_animation: bool
    use_base_data: bool
    use_inventory: bool
    use_script: bool
    use_def_pack_list: bool # since Skyrim
    use_attack_data: bool # since Skyrim
    use_keywords: bool # since Skyrim

##: xEdit marks these as unknown_is_unused, at least in Skyrim, but it makes no
# sense because it also marks all 32 of its possible flags as known
class BipedFlags(Flags):
    """Base Biped flags element. Includes logic for checking if armor/clothing
    can be marked as playable. Should be subclassed to add the appropriate
    flags and, if needed, the non-playable flags."""
    _not_playable_flags: set[str] = set()

    @property
    def any_body_flag_set(self) -> bool:
        check_flags = set(type(self)._names) - type(self)._not_playable_flags
        return any(getattr(self, flg_name) for flg_name in check_flags)

# Sort Keys -------------------------------------------------------------------
fid_key = attrgetter_cache[u'fid']

_perk_type_to_attrs = {
    0: attrgetter_cache[('pe_quest', 'pe_quest_stage')],
    1: attrgetter_cache['pe_ability'],
    2: attrgetter_cache[('pe_entry_point', 'pe_function')],
}

def perk_effect_key(e):
    """Special sort key for PERK effects."""
    perk_effect_type = e.pe_type
    # The first three are always present, the others depend on the perk
    # effect's type
    extra_vals = _perk_type_to_attrs[perk_effect_type](e)
    if not isinstance(extra_vals, tuple):
        # Second case from above, only a single attribute returned.
        # DATA subrecords are sometimes absent after the PRKE subrecord,
        # leading to a None for pe_ability - sort those last (valid IDs
        # shouldn't be 0)
        return (e.pe_rank, e.pe_priority, perk_effect_type,
                extra_vals or NONE_FID)
    else:
        return e.pe_rank, e.pe_priority, perk_effect_type, *extra_vals

def gen_coed_key(base_attrs: tuple[str, ...]):
    """COED is optional, so all of its attrs may be None. Account
    for that to avoid TypeError when some entries have COED present
    and some don't."""
    base_attrgetter = attrgetter_cache[base_attrs]
    def _ret_key(e):
        return (*base_attrgetter(e), e.item_condition or 0.0,
                e.item_owner or NONE_FID, e.item_global or NONE_FID)
    return _ret_key

# Constants -------------------------------------------------------------------

# Null strings (for default empty byte arrays)
null1 = b'\x00'
null2 = null1 * 2
null3 = null1 * 3
null4 = null1 * 4

# TES4 Group/Top Types
group_types = {0: 'Top', 1: 'World Children', 2: 'Interior Cell Block',
               3: 'Interior Cell Sub-Block', 4: 'Exterior Cell Block',
               5: 'Exterior Cell Sub-Block', 6: 'Cell Children',
               7: 'Topic Children', 8: 'Cell Persistent Children',
               9: 'Cell Temporary Children',
               10: 'Cell Visible Distant Children/Quest Children'}

# Helpers ---------------------------------------------------------------------
def get_structs(struct_format):
    """Create a struct and return bound unpack, pack and size methods in a
    tuple."""
    _struct = structs_cache[struct_format]
    return _struct.unpack, _struct.pack, _struct.size

def ambient_lighting_attrs(attr_prefix: str) -> list[str]:
    """Helper method for generating a ton of repetitive attributes that are
    shared between a couple record types (wbAmbientColors in xEdit)."""
    color_types = [f'directional_{t}' for t in (
        'x_plus', 'x_minus', 'y_plus', 'y_minus', 'z_plus', 'z_minus')]
    color_types.append('specular')
    color_iters = chain.from_iterable(color_attrs(d) for d in color_types)
    ambient_lighting = [f'{attr_prefix}_ac_{x}' for x in color_iters]
    return ambient_lighting + [f'{attr_prefix}_ac_scale']

def color_attrs(color_attr_pfx: str, *,
        rename_alpha: bool = False) -> list[str]:
    """Helper method for generating red/green/blue/alpha color attributes. Note
    that alpha is commonly unused when Bethesda uses this 4-float style of
    colors and you may have to pass rename_alpha=True to name that attribute
    '*_unused' instead of '*_alpha' if a separate alpha attribute exists."""
    return [f'{color_attr_pfx}_{c}' for c in (
        'red', 'green', 'blue', ('unused' if rename_alpha else 'alpha'))]

def color3_attrs(color_attr_pfx: str) -> list[str]:
    """Helper method for generating red/green/blue color attributes."""
    return [f'{color_attr_pfx}_{c}' for c in ('red', 'green', 'blue')]

def _gen_3d_attrs(attr_prefix: str) -> list[str]:
    """Internal helper for position_attrs et al."""
    return [f'{attr_prefix}_{d}' for d in ('x', 'y', 'z')]

def position_attrs(attr_prefix: str) -> list[str]:
    """Helper method for generating X/Y/Z position attributes."""
    return _gen_3d_attrs(f'{attr_prefix}_pos')

def rotation_attrs(attr_prefix: str) -> list[str]:
    """Helper method for generating X/Y/Z rotation attributes."""
    return _gen_3d_attrs(f'{attr_prefix}_rot')

def velocity_attrs(attr_prefix: str) -> list[str]:
    """Helper method for generating X/Y/Z velocity attributes."""
    return _gen_3d_attrs(f'{attr_prefix}_vel')

# Distributors ----------------------------------------------------------------
# Shared distributor for LENS records
lens_distributor = {
    b'DNAM': 'fade_distance_radius_scale',
    b'LFSP': {
        b'DNAM': 'lens_flare_sprites',
    },
}

# Shared distributor for PERK records
perk_distributor = {
    b'DESC': {
        b'CTDA|CIS1|CIS2': 'conditions',
        b'DATA': 'perk_trait',
    },
    b'PRKE': {
        b'CTDA|CIS1|CIS2|DATA': 'perk_effects',
    },
}
