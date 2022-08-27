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
"""Menu items for the _main_ menu of the mods tab - their window attribute
points to BashFrame.modList singleton."""

import re
from .dialogs import CreateNewPlugin
from .frames import PluginChecker
from .. import bass, bosh, balt, load_order
from .. import bush # for Mods_LoadListData, Mods_LoadList
from .. import exception
from ..balt import ItemLink, CheckLink, BoolLink, EnabledLink, ChoiceLink, \
    SeparatorLink, Link, MultiLink
from ..bolt import FName, dict_sort
from ..gui import BusyCursor, copy_text_to_clipboard, get_shift_down, \
    get_ctrl_down
from ..parsers import CsvParser

__all__ = [u'Mods_EsmsFirst', u'Mods_LoadList', u'Mods_SelectedFirst',
           u'Mods_OblivionVersion', u'Mods_CreateBlankBashedPatch',
           u'Mods_CreateBlank', u'Mods_ListMods', u'Mods_ListBashTags',
           u'Mods_CleanDummyMasters', u'Mods_AutoGhost', u'Mods_LockLoadOrder',
           u'Mods_ScanDirty', u'Mods_CrcRefresh', u'Mods_AutoESLFlagBP',
           u'Mods_LockActivePlugins', u'Mods_PluginChecker',
           u'Mods_ExportBashTags', u'Mods_ImportBashTags',
           u'Mods_ClearManualBashTags', u'Mods_OpenLOFileMenu']

# "Load" submenu --------------------------------------------------------------
class _Mods_LoadListData(balt.ListEditorData):
    """Data capsule for load list editing dialog."""
    def __init__(self, parent, loadListsDict):
        self.loadListDict = loadListsDict
        #--GUI
        balt.ListEditorData.__init__(self,parent)
        self.showRename = True
        self.showRemove = True

    def getItemList(self):
        """Returns load list keys in alpha order."""
        return sorted(self.loadListDict, key=lambda a: a.lower())

    def rename(self,oldName,newName):
        """Renames oldName to newName."""
        #--Right length?
        if len(newName) == 0 or len(newName) > 64:
            balt.showError(self.parent,
                _(u'Name must be between 1 and 64 characters long.'))
            return False
        #--Rename
        self.loadListDict[newName] = self.loadListDict[oldName]
        del self.loadListDict[oldName]
        return newName

    def remove(self,item):
        """Removes load list."""
        del self.loadListDict[item]
        return True

class Mods_LoadList(ChoiceLink):
    """Add active mods list links."""
    __uninitialized = {}
    loadListsDict = __uninitialized

    def __init__(self):
        super(Mods_LoadList, self).__init__()
        _self = self
        #--Links
        class __Activate(ItemLink):
            """Common methods used by Links de/activating mods."""
            def _refresh(self): self.window.RefreshUI(refreshSaves=True)
            def _selectExact(self, mods):
                errorMessage = bosh.modInfos.lo_activate_exact(mods)
                self._refresh()
                if errorMessage: self._showError(errorMessage, self._text)
        class _All(__Activate):
            _text = _('Activate All')
            _help = _('Activate all plugins.')
            def Execute(self):
                """Select all mods."""
                try:
                    bosh.modInfos.lo_activate_all()
                except exception.PluginsFullError:
                    self._showError(_('Plugin list is full, so some plugins '
                                      'were skipped.'),
                        title=_('Select All - Too Many Plugins'))
                except exception.BoltError as e:
                    self._showError(f'{e}', _('Select All'))
                self._refresh()
        class _None(__Activate):
            _text = _('De-activate All')
            _help = _('De-activate all plugins.')
            def Execute(self): self._selectExact([])
        class _Selected(__Activate):
            _text = _('Activate Selected')
            _help = _('Activate only the currently selected plugins.')
            def Execute(self):
                self._selectExact(self.window.GetSelected())
        class _Edit(ItemLink):
            _text = _('Edit Active Plugins Lists...')
            _help = _('Display a dialog to rename/remove active plugins '
                      'lists.')
            def Execute(self):
                editorData = _Mods_LoadListData(self.window, _self.load_lists)
                balt.ListEditor.display_dialog(
                    self.window, _('Active Plugins Lists'), editorData)
        class _SaveLink(EnabledLink):
            _text = _('Save Active Plugins List')
            _help = _('Save the currently active plugin to a new active '
                      'plugins list.')
            def _enable(self): return bool(load_order.cached_active_tuple())
            def Execute(self):
                newItem = self._askText(_('Save currently active plugins list '
                                          'as:'))
                if not newItem: return
                if len(newItem) > 64:
                    message = _('Active plugins list name must be between '
                                '1 and 64 characters long.')
                    return self._showError(message)
                _self.load_lists[newItem] = list(
                    load_order.cached_active_tuple())
        self.extraItems = [_All(), _None(), _Selected(), _SaveLink(), _Edit(),
                           SeparatorLink()]
        class _LoListLink(__Activate):
            def Execute(self):
                """Activate mods in list."""
                mods = set(_self.load_lists[self._text])
                mods = [m for m in self.window.data_store if m in mods]
                self._selectExact(mods)
            @property
            def link_help(self):
                return _('Activate plugins in the %(list_name)s list.') % {
                    'list_name': self._text}
        self.__class__.choiceLinkType = _LoListLink

    @property
    def load_lists(self):
        """Get the load lists, since those come from BashLoadOrders.dat we must
        wait for this being initialized in ModInfos.__init__"""
        if self.__class__.loadListsDict is self.__class__.__uninitialized:
            loadListData = load_order.get_active_mods_lists()
            loadListData[u'Vanilla'] = [
                FName(x) for x in bush.game.bethDataFiles if x.endswith(
                    u'.esm') # but avoid activating modding esms for oblivion
                and (not re.match(bosh.reOblivion.pattern, x, re.I)
                     or x == u'oblivion.esm')]
            self.__class__.loadListsDict = loadListData
        return self.__class__.loadListsDict

    @property
    def _choices(self):
        return sorted(self.load_lists, key=lambda a: a.lower())

# "Sort by" submenu -----------------------------------------------------------
class Mods_EsmsFirst(CheckLink, EnabledLink):
    """Sort esms to the top."""
    _help = _(u'Sort masters by type. Always on if current sort is Load Order.')
    _text = _(u'Type')

    def _enable(self): return not self.window.forceEsmFirst()
    def _check(self): return self.window.esmsFirst

    def Execute(self):
        self.window.esmsFirst = not self.window.esmsFirst
        self.window.SortItems()

class Mods_SelectedFirst(CheckLink):
    """Sort loaded mods to the top."""
    _text = _('Loaded')
    _help = _('Sort active, merged and imported plugins to the top.')

    def _check(self): return self.window.selectedFirst

    def Execute(self):
        self.window.selectedFirst = not self.window.selectedFirst
        self.window.SortItems()

# "Oblivion.esm" submenu ------------------------------------------------------
class Mods_OblivionVersion(CheckLink, EnabledLink):
    """Specify/set Oblivion version."""
    _help = _(u'Specify/set Oblivion version')

    def __init__(self, version_key, setProfile=False):
        super(Mods_OblivionVersion, self).__init__()
        self._version_key = self._text = version_key
        self.setProfile = setProfile

    def _check(self): return bosh.modInfos.voCurrent == self._version_key

    def _enable(self):
        return bosh.modInfos.voCurrent is not None \
               and self._version_key in bosh.modInfos.voAvailable

    def Execute(self):
        """Handle selection."""
        if bosh.modInfos.voCurrent == self._version_key: return
        bosh.modInfos.setOblivionVersion(self._version_key)
        self.window.RefreshUI(refreshSaves=True) # True: refresh save's masters
        if self.setProfile:
            bosh.saveInfos.set_profile_attr(bosh.saveInfos.localSave,
                                            'vOblivion', self._version_key)
        Link.Frame.set_bash_frame_title()

# "File" submenu --------------------------------------------------------------
class Mods_CreateBlankBashedPatch(ItemLink):
    """Create a new bashed patch."""
    _text = _(u'New Bashed Patch')
    _help = _(u'Create a new Bashed Patch.')
    _keyboard_hint = 'Ctrl+Shift+N'

    def Execute(self):
        self.window.new_bashed_patch()

class Mods_CreateBlank(ItemLink):
    """Create a new blank mod."""
    _text = _(u'New Plugin...')
    _help = _(u'Create a new blank plugin.')
    _keyboard_hint = 'Ctrl+N'

    def Execute(self):
        CreateNewPlugin.display_dialog(self.window)

#------------------------------------------------------------------------------
class Mods_ListMods(ItemLink):
    """Copies list of mod files to clipboard."""
    _text = _('List Plugins...')
    _help = _('Copies list of active plugins to clipboard.')

    def Execute(self):
        #--Get masters list
        list_txt = bosh.modInfos.getModList(showCRC=get_shift_down(),
                                            showVersion=not get_ctrl_down())
        copy_text_to_clipboard(list_txt)
        self._showLog(list_txt, title=_(u'Active Plugins'), fixedFont=False)

#------------------------------------------------------------------------------
# Basically just a convenient 'whole LO' version of Mod_ListBashTags
class Mods_ListBashTags(ItemLink):
    """Copies list of bash tags to clipboard."""
    _text = _(u'List Bash Tags...')
    _help = _(u'Copies list of bash tags to clipboard.')

    def Execute(self):
        tags_text = bosh.modInfos.getTagList()
        copy_text_to_clipboard(tags_text)
        self._showLog(tags_text, title=_(u'Bash Tags'), fixedFont=False)

#------------------------------------------------------------------------------
class Mods_CleanDummyMasters(EnabledLink):
    """Clean up after using a 'Create Dummy Masters...' command."""
    _text = _(u'Remove Dummy Masters...')
    _help = _(u"Clean up after using a 'Create Dummy Masters...' command")

    def _enable(self):
        for fileInfo in bosh.modInfos.values():
            if fileInfo.header.author == u'BASHED DUMMY':
                return True
        return False

    def Execute(self):
        remove = []
        for fileName, fileInfo in bosh.modInfos.items():
            if fileInfo.header.author == u'BASHED DUMMY':
                remove.append(fileName)
        remove = load_order.get_ordered(remove)
        self.window.DeleteItems(items=remove, order=False,
                                dialogTitle=_(u'Delete Dummy Masters'))

#------------------------------------------------------------------------------
class Mods_AutoGhost(BoolLink):
    """Toggle Auto-ghosting."""
    _text, _bl_key = _(u'Auto-Ghost'), u'bash.mods.autoGhost'
    _help = _(u'Toggles whether or not to automatically ghost all disabled '
              u'mods.')

    def Execute(self):
        super(Mods_AutoGhost, self).Execute()
        self.window.RefreshUI(redraw=bosh.modInfos.autoGhost(force=True),
                              refreshSaves=False)

class Mods_AutoESLFlagBP(BoolLink):
    """Automatically flags built Bashed Patches as ESLs. This is safe, since
    BPs can never contain new records, only overrides."""
    _text = _(u'ESL-Flag Bashed Patches')
    _help = _(u'Automatically flags any built Bashed Patches as ESLs, freeing '
              u'up a load order slot.')
    _bl_key = u'bash.mods.auto_flag_esl'

class Mods_ScanDirty(BoolLink):
    """Read mod CRC's to check for dirty mods."""
    _text = _(u"Check mods against LOOT's dirty mod list")
    _help = _(u'Display a tooltip if mod is dirty and underline dirty mods.')
    _bl_key = u'bash.mods.scanDirty'

    def Execute(self):
        super(Mods_ScanDirty, self).Execute()
        self.window.RefreshUI(refreshSaves=False) # update all mouse tips

class Mods_LockLoadOrder(CheckLink):
    """Turn on Lock Load Order feature."""
    _text = _(u'Lock Load Order')
    _help = _(u'Will reset mod Load Order to whatever Wrye Bash has saved for'
             u' them whenever Wrye Bash refreshes data/starts up.')

    def _check(self): return load_order.locked

    def Execute(self):
        def _show_lo_lock_warning():
            message = _(u'Lock Load Order is a feature which resets load '
                        u'order to a previously memorized state. While this '
                        u'feature is good for maintaining your load order, it '
                        u'will also undo any load order changes that you have '
                        u'made outside Bash.')
            return self._askContinue(message, u'bash.load_order.lock.continue',
                                     title=_(u'Lock Load Order'))
        load_order.toggle_lock_load_order(_show_lo_lock_warning)

class Mods_LockActivePlugins(BoolLink, EnabledLink):
    """Turn on Lock Active Plugins, needs Lock Load Order to be on first."""
    _text = _(u'Lock Active Plugins')
    _help = _(u"Enhances 'Lock Load Order' to also detect when mods are "
              u'enabled or disabled and to undo those changes too.')
    _bl_key = u'bash.load_order.lock_active_plugins'

    def _enable(self): return load_order.locked # needs Lock LO to be on

#------------------------------------------------------------------------------
class Mods_CrcRefresh(ItemLink):
    """Recalculate crcs for all mods"""
    _text = _(u'Recalculate CRCs')
    _help = _(u'Clean stale CRCs from cache')

    @balt.conversation
    def Execute(self):
        message = u'== %s' % _(u'Mismatched CRCs') + u'\n\n'
        with BusyCursor(): pairs = bosh.modInfos.refresh_crcs()
        mismatched = {k: v for k, v in pairs.items() if v[0] != v[1]}
        if mismatched:
            message += u'  * ' + u'\n  * '.join(
                [f'{k}: cached {v[1]:08X} real {v[0]:08X}' for k, v in
                 mismatched.items()])
            self.window.RefreshUI(redraw=mismatched, refreshSaves=False)
        else: message += _(u'No stale cached CRC values detected')
        self._showWryeLog(message)

#------------------------------------------------------------------------------
class Mods_PluginChecker(ItemLink):
    """Launches the Plugin Checker. More discoverable alternative to the teensy
    icon at the bottom."""
    _text = _(u'Plugin Checker...')
    _help = _(u'Checks your loaded plugins for various problems and shows a '
              u'configurable report.')

    def Execute(self):
        PluginChecker.create_or_raise()

#------------------------------------------------------------------------------
class _Mods_BashTags(ItemLink, CsvParser):
    pass

class Mods_ExportBashTags(_Mods_BashTags):
    """Writes all currently applied bash tags to a CSV file."""
    _text = _(u'Export Bash Tags...')
    _help = _(u'Exports all currently applied bash tags to a CSV file.')
    _csv_header = u'Plugin', u'Tags'

    def Execute(self):
        exp_path = self._askSave(title=_('Export bash tags to CSV file:'),
            defaultDir=bass.dirs['patches'], defaultFile='SavedTags.csv',
            wildcard='*.csv')
        if not exp_path: return
        self.plugins_exported = 0
        self.write_text_file(exp_path)
        self._showOk(_(u'Exported tags for %(exp_num)u plugin(s) to '
                       u'%(exp_path)s.') % {u'exp_num': self.plugins_exported,
                                            u'exp_path': exp_path})

    def _write_rows(self, out):
        for pl_name, p in dict_sort(bosh.modInfos):
            curr_tags = p.getBashTags()
            if curr_tags:
                out.write(f'"{pl_name}","{u", ".join(sorted(curr_tags))}"\n')
                self.plugins_exported += 1

#------------------------------------------------------------------------------
class Mods_ImportBashTags(_Mods_BashTags):
    """Reads bash tags from a CSV file and applies them to the current plugins
    (as far as possible)."""
    _text = _(u'Import Bash Tags...')
    _help = _(u'Imports applied bash tags from a CSV file.')

    def Execute(self):
        if not self._askWarning(
            _(u'This will permanently replace applied bash tags with ones '
              u'from a previously exported CSV file. Plugins that are not '
              u'listed in the CSV file will not be touched.') + u'\n\n' +
            _(u'Are you sure you want to proceed?')):
            return
        imp_path = self._askOpen(title=_('Import bash tags from CSV file:'),
            defaultDir=bass.dirs['patches'], defaultFile='SavedTags.csv',
            wildcard='*.csv')
        if not imp_path: return
        self.first_line = True
        self.plugins_imported = []
        try:
            self.read_csv(imp_path)
        except exception.BoltError:
            self._showError(_(u'The selected file is not a valid '
                              u'bash tags CSV export.'))
            return
        self.window.RefreshUI(redraw=self.plugins_imported, refreshSaves=False)
        self._showOk(
            _(u'Imported tags for %u plugin(s).') % len(self.plugins_imported))

    def _parse_line(self, csv_fields):
        if self.first_line: # header validation
            self.first_line = False
            if len(csv_fields) != 2 or csv_fields != [u'Plugin', u'Tags']:
                raise exception.BoltError(u'Header error: %s' % (csv_fields,))
            return
        pl_name, curr_tags = csv_fields
        if (pl_name := FName(pl_name)) in bosh.modInfos:
            target_tags = {t.strip() for t in curr_tags.split(u',')}
            target_pl = bosh.modInfos[pl_name]
            # Only import if doing this would actually change anything and mark
            # as non-automatic (otherwise they'll just get deleted immediately)
            if target_pl.getBashTags() != target_tags:
                self.plugins_imported.append(pl_name)
                target_pl.setBashTags(target_tags)
                target_pl.set_auto_tagged(False)

#------------------------------------------------------------------------------
class Mods_ClearManualBashTags(ItemLink):
    """Removes all manually applied tags."""
    _text = _(u'Clear Manual Bash Tags')
    _help = _(u'Removes all manually applied bash tags.')

    def Execute(self):
        if not self._askWarning(
                _(u'This will permanently and irreversibly remove all '
                  u'manually applied bash tags from all plugins. Tags from '
                  u'plugin descriptions, the LOOT masterlist/userlist and '
                  u'BashTags files will be left alone.') + u'\n\n' +
                _(u'Are you sure you want to proceed?')):
            return
        pl_reset = []
        for pl_name, p in bosh.modInfos.items():
            if not p.is_auto_tagged():
                pl_reset.append(pl_name)
                p.set_auto_tagged(True)
                p.reloadBashTags()
        self.window.RefreshUI(redraw=pl_reset, refreshSaves=False)
        self._showOk(_(u'Cleared tags from %u plugin(s).') % len(pl_reset))

#------------------------------------------------------------------------------
class _Mods_OpenLOFile(ItemLink):
    """Opens a load order file in the system's default text editor."""
    def __init__(self, lo_file_path):
        super(_Mods_OpenLOFile, self).__init__()
        self._lo_file_path = lo_file_path
        lo_file_name = lo_file_path.stail
        self._text = _(u'Open %s') % lo_file_name
        self._help = _(u'Opens the load order management file "%s" in a text '
                       u'editor.') % lo_file_name

    def Execute(self):
        self._lo_file_path.start()

class Mods_OpenLOFileMenu(MultiLink):
    """Shows one or more links for opening LO management files."""
    def _links(self):
        return [_Mods_OpenLOFile(lo_f) for lo_f in load_order.get_lo_files()]
