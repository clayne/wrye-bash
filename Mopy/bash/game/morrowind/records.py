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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module contains the Morrowind record classes. Also contains records
and subrecords used for the saves - see MorrowindSaveHeader for more
information."""
from ... import brec
from ...bolt import Flags
from ...brec import MelBase, MelSet, MelString, MelStruct, MelArray, \
    MreHeaderBase, MelUnion, SaveDecider, MelNull, MelSequential, MelRecord, \
    MelGroup, MelGroups, MelUInt8, MelDescription, MelUInt32, MelColorO,\
    MelOptStruct, MelCounter, MelRefScale, MelOptSInt32, MelRef3D, \
    MelOptFloat, MelOptUInt32, MelIcons, MelFloat, null1, null3, MelSInt32, \
    MelFixedString, FixedString, AutoFixedString, MreGmstBase, MelOptUInt8, \
    MreLeveledListBase, MelUInt16
if brec.MelModel is None:

    class _MelModel(MelGroup):
        def __init__(self):
            super(_MelModel, self).__init__(u'model',
                MelString(b'MODL', u'modPath'))

    brec.MelModel = _MelModel
from ...brec import MelModel

#------------------------------------------------------------------------------
# Utilities -------------------------------------------------------------------
#------------------------------------------------------------------------------
class MelAIAccompanyPackage(MelOptStruct):
    """Deduplicated from AI_E and AI_F (see below)."""
    def __init__(self, ai_package_sig):
        super(MelAIAccompanyPackage, self).__init__(ai_package_sig,
            u'3fH32sBs', u'dest_x', u'dest_y', u'dest_z', u'package_duration',
            (FixedString(32), u'package_id'), (u'unknown_marker', 1),
            (u'unused1', null1))

class MelAIPackages(MelGroups):
    """Handles the AI_* and CNDT subrecords, which have the additional
    complication that they may occur in any order."""
    def __init__(self):
        super(MelAIPackages, self).__init__(u'aiPackages',
            MelUnion({
                b'AI_A': MelStruct(b'AI_A', u'=32sB',
                    (FixedString(32), u'package_name'),
                    (u'unknown_marker', 1)),
                b'AI_E': MelAIAccompanyPackage(b'AI_E'),
                b'AI_F': MelAIAccompanyPackage(b'AI_F'),
                b'AI_T': MelStruct(b'AI_T', u'3fB3s', u'dest_x', u'dest_y',
                    u'dest_z', (u'unknown_marker', 1), (u'unused1', null1)),
                b'AI_W': MelStruct(b'AI_W', u'=2H10B', u'wanter_distance',
                    u'wanter_duration', u'time_of_day', u'idle_1', u'idle_2',
                    u'idle_3', u'idle_4', u'idle_5', u'idle_6', u'idle_7',
                    u'idle_8', (u'unknown_marker', 1)),
            }),
            # Only present for AI_E and AI_F, but should be fine since the
            # default for MelString is None, so won't be dumped unless already
            # present (i.e. the file is already broken)
            MelString(b'CNDT', u'cell_name'),
        )

#------------------------------------------------------------------------------
class MelArmorData(MelGroups):
    """Handles the INDX, BNAM and CNAM subrecords shared by ARMO and CLOT."""
    def __init__(self):
        super(MelArmorData, self).__init__(u'armor_data',
            MelUInt8(b'INDX', u'biped_object'),
            MelString(b'BNAM', u'armor_name_male'),
            MelString(b'CNAM', u'armor_name_female'),
        )

#------------------------------------------------------------------------------
class MelDestinations(MelGroups):
    """Handles the common DODT/DNAM subrecords."""
    def __init__(self):
        super(MelDestinations, self).__init__(u'cell_travel_destinations',
            MelStruct(b'DODT', u'6f', u'dest_pos_x', u'dest_pos_y',
                u'dest_pos_z', u'dest_rot_x', u'dest_rot_y', u'dest_rot_z'),
            MelString(b'DNAM', u'dest_cell_name'),
        )

#------------------------------------------------------------------------------
class MelEffects(MelGroups):
    """Handles the list of ENAM structs present on several records."""
    def __init__(self):
        super(MelEffects, self).__init__(u'effects',
            MelStruct(b'ENAM', u'H2b5I', u'effect_index', u'skill_affected',
                u'attribute_affected', u'ench_range', u'ench_area',
                u'ench_duration', u'ench_magnitude_min',
                u'ench_magnitude_max'),
        )

#------------------------------------------------------------------------------
class MelItems(MelGroups):
    """Wraps MelGroups for the common task of defining a list of items."""
    def __init__(self):
        super(MelItems, self).__init__(u'items',
            MelStruct(b'NPCO', u'I32s', u'count', (FixedString(32), u'item')),
        )

#------------------------------------------------------------------------------
class MelMWEnchantment(MelString):
    """Handles ENAM, Morrowind's version of EITM."""
    def __init__(self):
        super(MelMWEnchantment, self).__init__(b'ENAM', u'enchantment')

#------------------------------------------------------------------------------
class MelMWFull(MelString):
    """Defines FNAM, Morrowind's version of FULL."""
    def __init__(self):
        super(MelMWFull, self).__init__(b'FNAM', u'full')

#------------------------------------------------------------------------------
class MelMWIcon(MelIcons):
    """Handles the common ITEX record, Morrowind's version of ICON."""
    def __init__(self):
        super(MelMWIcon, self).__init__(icon_sig=b'ITEX', mico_attr=u'')

#------------------------------------------------------------------------------
class MelMWId(MelString):
    """Wraps MelString to define a common NAME handler."""
    def __init__(self):
        super(MelMWId, self).__init__(b'NAME', u'mw_id')

#------------------------------------------------------------------------------
class MelMWSpells(MelGroups):
    """Handles NPCS, Morrowind's version of SPLO."""
    def __init__(self):
        super(MelMWSpells, self).__init__(u'spells',
            MelFixedString(b'NPCS', u'spell_id', 32),
        )

#------------------------------------------------------------------------------
class MelReference(MelSequential):
    """Defines a single 'reference', which is Morrowind's version of REFRs in
    later games."""
    def __init__(self):
        super(MelReference, self).__init__(
            MelUInt32(b'FRMR', u'object_index'),
            MelMWId(),
            MelBase(b'UNAM', u'ref_blocked_marker'),
            MelRefScale(),
            MelString(b'ANAM', u'ref_owner'),
            MelString(b'BNAM', u'global_variable'),
            MelString(b'CNAM', u'ref_faction'),
            MelOptSInt32(b'INDX', u'ref_faction_rank'),
            MelString(b'XSOL', u'ref_soul'),
            MelOptFloat(b'XCHG', u'enchantment_charge'),
            ##: INTV should have a decider - uint32 or float, depending on
            # object type
            MelBase(b'INTV', u'remaining_usage'),
            MelOptUInt32(b'NAM9', u'gold_value'),
            MelDestinations(),
            MelOptUInt32(b'FLTV', u'lock_level'),
            MelString(b'KNAM', u'key_name'),
            MelString(b'TNAM', u'trap_name'),
            MelBase(b'ZNAM', u'ref_disabled_marker'),
            MelRef3D(),
        )

#------------------------------------------------------------------------------
class MelSavesOnly(MelSequential):
    """Record element that only loads contents if the input file is a save
    file."""
    def __init__(self, *elements):
        super(MelSavesOnly, self).__init__(*(MelUnion({
            True: element,
            False: MelNull(b'ANY')
        }, decider=SaveDecider()) for element in elements))

#------------------------------------------------------------------------------
class MelScriptId(MelString):
    """Handles the common SCRI subrecord."""
    def __init__(self):
        super(MelScriptId, self).__init__(b'SCRI', u'script_id'),

#------------------------------------------------------------------------------
class MreLeveledList(MreLeveledListBase):
    """Base class for LEVC and LEVI."""
    _lvl_flags = Flags(0, Flags.getNames(
        u'calcFromAllLevels',
        u'calcForEachItem', # LEVI only, but will be ignored for LEVC so fine
    ))
    top_copy_attrs = (u'chanceNone',)
    entry_copy_attrs = (u'listId', u'level') # no count

    # Bad names to mirror the other games (needed by MreLeveledListBase)
    melSet = MelSet(
        MelMWId(),
        MelUInt32(b'DATA', (_lvl_flags, u'flags')),
        MelUInt8(b'NNAM', u'chanceNone'),
        MelCounter(MelUInt32(b'INDX', u'entry_count'), counts=u'entries'),
        MelGroups(u'entries',
            MelString(b'INAM', u'listId'),
            MelUInt16(b'INTV', u'level'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Shared (plugins + saves) record classes -------------------------------------
#------------------------------------------------------------------------------
class MreTes3(MreHeaderBase):
    """TES3 Record. File header."""
    rec_sig = b'TES3'

    melSet = MelSet(
        MelStruct(b'HEDR', u'fI32s256sI', (u'version', 1.3), u'esp_flags',
            (AutoFixedString(32), u'author'),
            (AutoFixedString(256), u'description'), u'numRecords'),
        MreHeaderBase.MelMasterNames(),
        MelSavesOnly(
            # Wrye Mash calls unknown1 'day', but that seems incorrect?
            MelStruct(b'GMDT', u'6f64sf32s', u'pc_curr_health',
                u'pc_max_health', u'unknown1', u'unknown2', u'unknown3',
                u'unknown4', (FixedString(64), u'curr_cell'), u'unknown5',
                (AutoFixedString(32), u'pc_name')),
            MelBase(b'SCRD', u'unknown_scrd'), # likely screenshot-related
            MelArray(u'screenshot_data',
                # Yes, the correct order is bgra
                MelStruct(b'SCRS', u'4B', u'blue', u'green', u'red', u'alpha'),
            ),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Plugins-only record classes -------------------------------------------------
#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator."""
    rec_sig = b'ACTI'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelMWFull(),
        MelScriptId(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAlch(MelRecord):
    """Potion."""
    rec_sig = b'ALCH'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelString(b'TEXT', u'book_text'),
        MelScriptId(),
        MelMWFull(),
        MelStruct(b'ALDT', u'f2I', u'potion_weight', u'potion_value',
            u'potion_auto_calc'),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAppa(MelRecord):
    """Alchemical Apparatus."""
    rec_sig = b'APPA'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelMWFull(),
        MelScriptId(),
        MelStruct(b'AADT', u'I2fI', u'appa_type', u'appa_quality',
            u'appa_weight', u'appa_value'),
        MelMWIcon(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor."""
    rec_sig = b'ARMO'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelMWFull(),
        MelScriptId(),
        MelStruct(b'AODT', u'If4I', u'armo_type', u'armo_weight',
            u'armo_value', u'armo_health', u'enchant_points', u'armor_rating'),
        MelMWIcon(),
        MelArmorData(),
        MelMWEnchantment(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreBody(MelRecord):
    """Body Parts."""
    rec_sig = b'BODY'

    _part_flags = Flags(0, Flags.getNames(u'part_female', u'part_playable'))

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelString(b'FNAM', u'race_name'),
        MelStruct(b'BYDT', u'4B', u'part_index', u'part_vampire',
            (_part_flags, u'part_flags'), u'part_type'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreBook(MelRecord):
    """Book."""
    rec_sig = b'BOOK'

    _scroll_flags = Flags(0, Flags.getNames(u'is_scroll'))

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelMWFull(),
        MelStruct(b'BKDT', u'f2IiI', u'book_weight', u'book_value',
            (_scroll_flags, u'scroll_flags'), u'skill_id', u'enchant_points'),
        MelScriptId(),
        MelMWIcon(),
        MelString(b'TEXT', u'book_text'),
        MelMWEnchantment(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreBsgn(MelRecord):
    """Birthsign."""
    rec_sig = b'BSGN'

    melSet = MelSet(
        MelMWId(),
        MelMWFull(),
        MelMWSpells(),
        MelString(b'TNAM', u'texture_filename'),
        MelDescription(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCell(MelRecord):
    """Cell."""
    rec_sig = b'CELL'

    _cell_flags = Flags(0, Flags.getNames(
        (0, u'is_interior_cell'),
        (1, u'has_water'),
        (2, u'illegal_to_sleep_here'),
        (7, u'behave_like_exterior'),
    ))

    melSet = MelSet(
        MelMWId(),
        MelStruct(b'DATA', u'3I', (_cell_flags, u'cell_flags'), u'cell_x',
            u'cell_y'),
        MelString(b'RGNN', u'region_name'),
        MelColorO(b'NAM5'),
        MelOptFloat(b'WHGT', u'water_height'),
        MelOptStruct(b'AMBI', u'12Bf', u'ambient_red', u'ambient_blue',
            u'ambient_green', u'unused_alpha1', u'sunlight_red',
            u'sunlight_blue', u'sunlight_green', u'unused_alpha2', u'fog_red',
            u'fog_blue', u'fog_green', u'unused_alpha3'),
        MelGroups(u'moved_references',
            MelUInt32(b'MVRF', u'reference_id'),
            MelString(b'CNAM', u'new_interior_cell'),
            # None here are on purpose - only present for exterior cells, and
            # zeroes are perfectly valid X/Y coordinates
            ##: Double-check the signeds - UESP does not list them either way
            MelOptStruct(b'CNDT', u'2i', (u'new_exterior_cell_x', None),
                (u'new_exterior_cell_y', None)),
            MelReference(),
        ),
        MelGroups(u'persistent_children',
            MelReference(),
        ),
        MelCounter(MelUInt32(b'NAM0', u'temporary_children_counter'),
            counts=u'temporary_children'),
        MelGroups(u'temporary_children',
            MelReference(),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClas(MelRecord):
    """Class."""
    rec_sig = b'CLAS'

    _class_flags = Flags(0, Flags.getNames(u'class_playable'))
    _ac_flags = Flags(0, Flags.getNames(
        u'ac_weapon',
        u'ac_armor',
        u'ac_clothing',
        u'ac_books',
        u'ac_ingredients',
        u'ac_picks',
        u'ac_probes',
        u'ac_lights',
        u'ac_apparatus',
        u'ac_repair_items',
        u'ac_misc',
        u'ac_spells',
        u'ac_magic_items',
        u'ac_potions',
        u'ac_training',
        u'ac_spellmaking',
        u'ac_enchanting',
        u'ac_repair',
    ))

    melSet = MelSet(
        MelMWId(),
        MelMWFull(),
        ##: UESP says 'alternating minor/major' skills - not sure what exactly
        # it means, check with real data
        MelStruct(b'CLDT', u'15I', u'primary1', u'primary2',
            u'specialization', u'minor1', u'major1', u'minor2', u'major2',
            u'minor3', u'major3', u'minor4', u'major4', u'minor5', u'major5',
            (_class_flags, u'class_flags'), (_ac_flags, u'auto_calc_flags')),
        MelDescription(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClot(MelRecord):
    """Clothing."""
    rec_sig = b'CLOT'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelMWFull(),
        MelStruct(b'CTDT', u'If2H', u'clot_type', u'clot_weight',
            u'clot_value', u'enchant_points'),
        MelScriptId(),
        MelMWIcon(),
        MelArmorData(),
        MelMWEnchantment(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCont(MelRecord):
    """Container."""
    rec_sig = b'CONT'

    _cont_flags = Flags(0, Flags.getNames(
        u'cont_organic',
        u'cont_respawns',
        u'default_unknown', # always set
    ))

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelMWFull(),
        MelFloat(b'CNDT', u'cont_weight'),
        MelUInt32(b'FLAG', (_cont_flags, u'cont_flags')),
        MelItems(),
        MelScriptId(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCrea(MelRecord):
    """Creature."""
    rec_sig = b'CREA'

    _crea_flags = Flags(0, Flags.getNames(
        u'biped', # names match those of MreCrea._flags in later games
        u'respawn',
        u'weaponAndShield',
        u'crea_none',
        u'swims',
        u'flies',
        u'walks',
        u'default_flags',
        u'essential',
        u'skeleton_blood',
        u'metal_blood',
    ))
    _ai_flags = Flags(0, Flags.getNames(
        u'ai_weapon',
        u'ai_armor',
        u'ai_clothing',
        u'ai_books',
        u'ai_ingredient',
        u'ai_picks',
        u'ai_probes',
        u'ai_lights',
        u'ai_apparatus',
        u'ai_repair_items',
        u'ai_misc',
        u'ai_spells',
        u'ai_magic_items',
        u'ai_potions',
        u'ai_training',
        u'ai_spellmaking',
        u'ai_enchanting',
        u'ai_repair',
    ))

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelString(b'CNAM', u'sound_gen_creature'),
        MelMWFull(),
        MelScriptId(),
        MelStruct(b'NPDT', u'24I', u'crea_type', u'crea_level',
            u'crea_strength', u'crea_intelligence', u'crea_willpower',
            u'crea_agility', u'crea_speed', u'crea_endurance',
            u'crea_personality', u'crea_luck', u'crea_health',
            u'crea_spell_points', u'crea_fatigue', u'crea_soul',
            u'crea_combat', u'crea_magic', u'crea_stealth',
            u'crea_attack_min_1', u'crea_attack_max_1', u'crea_attack_min_2',
            u'crea_attack_max_2', u'crea_attack_min_3', u'crea_attack_max_3',
            u'crea_gold'),
        MelUInt32(b'FLAG', (_crea_flags, u'crea_flags')),
        MelRefScale(),
        MelItems(),
        MelMWSpells(),
        MelStruct(b'AIDT', u'Bs3B3sI', u'ai_hello', (u'unknown1', null1),
            u'ai_fight', u'ai_flee', u'ai_alarm', (u'unknown2', null3),
            (_ai_flags, u'ai_flags')),
        MelDestinations(),
        MelAIPackages(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDial(MelRecord):
    """Dialog Topic."""
    rec_sig = b'DIAL'

    melSet = MelSet(
        MelMWId(),
        MelUInt8(b'DATA', u'dialogue_type'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDoor(MelRecord):
    """Door."""
    rec_sig = b'DOOR'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelMWFull(),
        MelScriptId(),
        MelString(b'SNAM', u'sound_open'),
        MelString(b'ANAM', u'sound_close'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEnch(MelRecord):
    """Enchantment."""
    rec_sig = b'ENCH'

    melSet = MelSet(
        MelMWId(),
        MelStruct(b'ENDT', u'4I', u'ench_type', u'ench_cost', u'ench_charge',
            u'ench_auto_calc'),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Faction."""
    rec_sig = b'FACT'

    melSet = MelSet(
        MelMWId(),
        MelMWFull(),
        MelGroups(u'ranks', # always 10
            MelString(b'RNAM', u'rank_name'),
        ),
        ##: Double-check that these are all unsigned (especially
        # rank_*_reaction), xEdit makes most of them signed (and puts them in
        # an enum, which makes no sense). Also, why couldn't Bethesda put these
        # into the ranks list up above?
        MelStruct(b'FADT', u'52I7iI', u'faction_attribute_1',
            u'faction_attribute_2', u'rank_1_attribute_1',
            u'rank_1_attribute_2', u'rank_1_skill_1', u'rank_1_skill_2',
            u'rank_1_reaction', u'rank_2_attribute_1', u'rank_2_attribute_2',
            u'rank_2_skill_1', u'rank_2_skill_2', u'rank_2_reaction',
            u'rank_3_attribute_1', u'rank_3_attribute_2', u'rank_3_skill_1',
            u'rank_3_skill_2', u'rank_3_reaction', u'rank_4_attribute_1',
            u'rank_4_attribute_2', u'rank_4_skill_1', u'rank_4_skill_2',
            u'rank_4_reaction', u'rank_5_attribute_1', u'rank_5_attribute_2',
            u'rank_5_skill_1', u'rank_5_skill_2', u'rank_5_reaction',
            u'rank_6_attribute_1', u'rank_6_attribute_2', u'rank_6_skill_1',
            u'rank_6_skill_2', u'rank_6_reaction', u'rank_7_attribute_1',
            u'rank_7_attribute_2', u'rank_7_skill_1', u'rank_7_skill_2',
            u'rank_7_reaction', u'rank_8_attribute_1', u'rank_8_attribute_2',
            u'rank_8_skill_1', u'rank_8_skill_2', u'rank_8_reaction',
            u'rank_9_attribute_1', u'rank_9_attribute_2', u'rank_9_skill_1',
            u'rank_9_skill_2', u'rank_9_reaction', u'rank_10_attribute_1',
            u'rank_10_attribute_2', u'rank_10_skill_1', u'rank_10_skill_2',
            u'rank_10_reaction', u'skill_1', u'skill_2', u'skill_3',
            u'skill_4', u'skill_5', u'skill_6', u'skill_7',
            u'hidden_from_pc'),
        MelGroups(u'relations', # bad names to match other games
            MelString(b'ANAM', u'faction'),
            MelSInt32(b'INTV', u'mod'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGlob(MelRecord):
    """Global."""
    rec_sig = b'GLOB'

    melSet = MelSet(
        MelMWId(),
        MelFixedString(b'FNAM', u'global_format', 1, u's'),
        MelFloat(b'FLTV', u'global_value'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MelGmstUnion(MelUnion):
    """Some GMSTs do not have one of the value subrecords - fall back to
    using the first letter of the NAME subrecord in those cases."""
    _fmt_mapping = {
        u'f': b'FLTV',
        u'i': b'INTV',
        u's': b'STRV',
    }

    def _get_element_from_record(self, record):
        if not hasattr(record, self.decider_result_attr):
            format_char = record.mw_id[0] if record.mw_id else u'i'
            return self._get_element(self._fmt_mapping[format_char])
        return super(MelGmstUnion, self)._get_element_from_record(record)

class MreGmst(MreGmstBase):
    """Game Setting."""
    melSet = MelSet(
        MelMWId(),
        MelGmstUnion({
            b'FLTV': MelFloat(b'FLTV', u'value'),
            b'INTV': MelSInt32(b'INTV', u'value'),
            b'STRV': MelString(b'STRV', u'value'),
        }),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreInfo(MelRecord):
    """Dialog Response."""
    rec_sig = b'INFO'

    melSet = MelSet(
        MelString(b'INAM', u'info_name_string'),
        MelString(b'PNAM', u'prev_info_name'),
        MelString(b'NNAM', u'next_info_name'),
        MelStruct(b'DATA', u'B3sIBbBs', u'dialogue_type', (u'unused1', null3),
            u'disposition', u'dialogue_rank', u'speaker_gender', u'pc_rank',
            (u'unused2', null1)),
        MelString(b'ONAM', u'actor_name'),
        MelString(b'RNAM', u'race_name'),
        MelString(b'CNAM', u'class_name'),
        MelString(b'FNAM', u'faction_name'),
        MelString(b'ANAM', u'cell_name'),
        MelString(b'DNAM', u'pc_faction_name'),
        MelString(b'SNAM', u'sound_name'),
        MelMWId(),
        MelGroups(u'conditions',
            MelString(b'SCVR', u'condition_string'),
            # None here are on purpose - 0 is a valid value, but only certain
            # conditions need these subrecords to be present
            MelOptUInt32(b'INTV', (u'comparison_int', None)),
            MelOptFloat(b'FLTV', (u'comparison_float', None)),
        ),
        MelString(b'BNAM', u'result_text'),
        MelOptUInt8(b'QSTN', u'quest_name'),
        MelOptUInt8(b'QSTF', u'quest_finished'),
        MelOptUInt8(b'QSTR', u'quest_restart'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIngr(MelRecord):
    """Ingredient."""
    rec_sig = b'INGR'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelMWFull(),
        MelStruct(b'IRDT', u'fI12i', u'ingr_weight', u'ingr_value',
            u'effect_index_1', u'effect_index_2', u'effect_index_3',
            u'effect_index_4', u'skill_id_1', u'skill_id_2', u'skill_id_3',
            u'skill_id_4', u'attribute_id_1', u'attribute_id_2',
            u'attribute_id_3', u'attribute_id_4'),
        MelScriptId(),
        MelMWIcon(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLand(MelRecord):
    """Landscape."""
    rec_sig = b'LAND'

    _data_type_flags = Flags(0, Flags.getNames( ##: Shouldn't we set/use these?
        u'include_vnml_vhgt_wnam',
        u'include_vclr',
        u'include_vtex',
    ))

    ##: No MelMWId, will that be a problem?
    melSet = MelSet(
        MelStruct(b'INTV', u'2I', u'land_x', u'land_y'),
        MelUInt32(b'DATA', (_data_type_flags, u'dt_flags')),
        # These are all very large and too complex to manipulate -> MelBase
        MelBase(b'VNML', u'vertex_normals'),
        MelBase(b'VHGT', u'vertex_height_map'),
        MelBase(b'WNAM', u'world_map_heights'),
        MelBase(b'VCLR', u'vertex_colors'),
        MelBase(b'VTEX', u'vertex_textures'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLevc(MreLeveledList):
    """Leveled Creature."""
    rec_sig = b'LEVC'
    __slots__ = []

#------------------------------------------------------------------------------
class MreLevi(MreLeveledList):
    """Leveled Item."""
    rec_sig = b'LEVI'
    __slots__ = []

#------------------------------------------------------------------------------
class MreLigh(MelRecord):
    """Light."""
    rec_sig = b'LIGH'

    _light_flags = Flags(0, Flags.getNames(
        u'dynamic', # Bad names to match the other games (for tweaks)
        u'canTake',
        u'negative',
        u'flickers',
        u'light_fire',
        u'offByDefault',
        u'flickerSlow',
        u'pulse',
        u'pulseSlow',
    ))

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelMWFull(),
        MelMWIcon(),
        MelStruct(b'LHDT', u'fIiI4BI', u'light_weight', u'light_value',
            u'light_time', u'light_red', u'light_green', u'light_blue',
            u'unused_alpha', (_light_flags, u'flags')),
        MelString(b'SNAM', u'sound_name'),
        MelScriptId(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLock(MelRecord):
    """Lockpicking Item."""
    rec_sig = b'LOCK'

    melSet = MelSet(
        MelMWId(),
        MelModel(),
        MelMWFull(),
        MelStruct(b'LKDT', u'fIfI', u'lock_weight', u'lock_value',
            u'lock_quality', u'lock_uses'),
        MelScriptId(),
        MelMWIcon(),
    )
    __slots__ = melSet.getSlotsUsed()
