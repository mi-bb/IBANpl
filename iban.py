#         _/_/_/  _/_/_/      _/_/    _/      _/  _/_/_/    _/
#          _/    _/    _/  _/    _/  _/_/    _/  _/    _/  _/
#         _/    _/_/_/    _/_/_/_/  _/  _/  _/  _/_/_/    _/
#        _/    _/    _/  _/    _/  _/    _/_/  _/        _/
#     _/_/_/  _/_/_/    _/    _/  _/      _/  _/        _/_/_/_/
#
#    Copyright (C) 2016-2026 Michal Babik
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-----------------------------------------------------------------------------#
import gettext

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from ibanpl import (sql_get_all_bank_no, sql_get_all_jorg,
                    chk_avail_update, bank_list_update, chk_iban,
                    sql_get_bank_info_frmt)
_ = gettext.translation("ibanpl", localedir="locale", fallback=True).gettext
#-----------------------------------------------------------------------------#
class AppWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)
        self.set_title("IBANpl v2.0.0")
        self.set_position(Gtk.WindowPosition.CENTER)
        vbox1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        lab = Gtk.Label()
        lab.set_label(_("Wybierz numery banku i jednostki organizacyjnej"))
        lab.set_margin_start(8)
        lab.set_margin_end(8)
        vbox1.pack_start(lab, False, True, 8)
        lab = Gtk.Label()
        lab.set_markup("XX <span foreground=\"magenta\">XXXX</span> "
            "<span foreground=\"blue\">XXXX</span> XXXX XXXX XXXX XXXX")
        vbox1.pack_start(lab, False, True, 8)
        hbox2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.cbox1 = Gtk.ComboBoxText()
        self.cbox2 = Gtk.ComboBoxText()
        but1 = Gtk.Button.new_with_label(_("Uaktualnij bazę"))
        but1.connect("clicked", self.bank_list_update)
        hbox2.pack_start(self.cbox1, True, True, 4)
        hbox2.pack_start(self.cbox2, True, True, 0)
        hbox2.pack_start(but1, False, True, 4)
        vbox1.pack_start(hbox2, False, True, 8)
        lab = Gtk.Label()
        lab.set_label(_("Lub wpisz numer konta:"))
        vbox1.pack_start(lab, False, True, 8)
        self.iban_entry = Gtk.Entry()
        self.iban_entry.set_tooltip_text(_("Wpisz ręcznie numer konta, aby "
                "pokazać\ninformacje o banku i zweryfikować jego "
                "poprawność.\nAby działał wybór numerów z list, to pole "
                "musi być puste"))
        vbox1.pack_start(self.iban_entry, False, True, 8)
        self.iban_corr = Gtk.Label()
        vbox1.pack_start(self.iban_corr, False, True, 8)
        fr1 = Gtk.Frame(label=_("Informacje o banku:"))
        alg1 = Gtk.Alignment(xalign=0.5, yalign=0.5, xscale=1, yscale=1)
        alg1.set_margin_start(10)
        alg1.set_margin_end(10)
        grid1 = Gtk.Grid()
        alg1.add(grid1)
        fr1.add(alg1)
        vbox1.pack_start(fr1, True, True, 8)
        alg1 = Gtk.Alignment(xalign=0.5, yalign=0.5, xscale=1, yscale=1)
        alg1.set_margin_start(8)
        alg1.set_margin_end(8)
        alg1.add(vbox1)
        self.add(alg1)
        self.lab_list1 = []
        self.lab_list2 = []
        l_lab = [_("Nazwa:"), _("Nazwa handlowa:")]
        for i, v in enumerate(l_lab):
            self.lab_list1.append(Gtk.Label())
            lb = Gtk.Label()
            lb.set_label(v)
            grid1.attach(lb, 0, i, 1, 1)
            grid1.attach(self.lab_list1[i], 1, i, 1, 1)
        l_lab = [_("Nazwa jednostki:"), _("Nazwa skr.:"), _("Adres:"),
                _("Adres:"), _("Poczta:"), _("Skr. poczt.:"), _("Tel.:"),
                _("Fax:"), _("Rozp. dział.:"), _("BIC:"), _("BIC SEPA:"),
                "www", _("Woj./Powiat:"), _("Adr. kor.:"), _("Adr. kor.:"),
                _("Adr. kor. skr. pocz.:"), _("Zrzeszenie:"),
                _("Nr rozl. jedn. nadrz.:")]
        for i, v in enumerate(l_lab):
            lb = Gtk.Label()
            lb.set_label(v)
            self.lab_list2.append(Gtk.Label())
            grid1.attach(lb, 0, i+2, 1, 1)
            grid1.attach(self.lab_list2[i], 1, i+2, 1, 1)

        self.clear_fields_jorg()

        self.refr_bank_list()
        self.refr_jorg_list()

        self.refr_bank_info()

        self.cbox1.connect("changed", self.combo1_change)
        self.cbox2.connect("changed", self.combo2_change)
        self.iban_entry.connect("changed", self.entry_change)

        self.connect("delete_event", Gtk.main_quit)
        self.connect("destroy", Gtk.main_quit)

    def combo1_change(self, combox):
        self.refr_jorg_list()

    def combo2_change(self, combox):
        if self.iban_entry.get_text() == '':
            self.refr_bank_info()

    def entry_change(self, gtkentry):
        acc = gtkentry.get_text()
        if acc == '':
            self.iban_corr.set_text('')
            return
        acc = acc.replace(' ','')
        acc = acc.replace('-','')
        if len(acc) > 5:
            self.refr_bank_info(acc[2:])
        r, d, acno = chk_iban(acc)
        st = ''
        if r:
            st = '<span foreground=\"green\">'
            gtkentry.set_text(acno)
        else:
            st = '<span foreground=\"red\">'
        self.iban_corr.set_markup(st + d + '</span>')

    def refr_bank_list(self):
        self.cbox1.remove_all()
        d, er = sql_get_all_bank_no()
        for i in d:
            self.cbox1.append_text(str(i[0]))
        self.cbox1.set_active(0)

    def refr_jorg_list(self):
        self.cbox2.remove_all()
        ct = self.cbox1.get_active_text()
        d, er = sql_get_all_jorg(int(ct))
        for i in d:
            t = str(i[0])
            while len(t) < 4:
                t = '0' + t
            self.cbox2.append_text(t)
        self.cbox2.set_active(0)

    def refr_bank_info(self, accno=None):
        if not accno: # from comboboxes
            acc1 = self.cbox1.get_active_text()
            acc2 = self.cbox2.get_active_text()
            if not acc1 or not acc2:
                return
            accno = acc1 + acc2
            self.iban_corr.set_text('')

        bank, jorg, er = sql_get_bank_info_frmt(accno)
        if er is not None:
            return
        if bank is not None: # bank info
            vals = (bank.bank_name, bank.bank_tname)
            for i, e in enumerate(self.lab_list1):
                e.set_text(str(vals[i]))
        else:
            self.clear_fields_bank()
        if jorg is not None: # jorg info
            vals = jorg.frmt_row()
            for i, e in enumerate(self.lab_list2):
                e.set_text(str(vals[i]))
        else:
            self.clear_fields_jorg()

    def clear_fields_bank(self):
        """Clears bank data fields"""
        for e in self.lab_list1:
            e.set_text("")

    def clear_fields_jorg(self):
        """Clears jorg data fields"""
        for e in self.lab_list2:
            e.set_text("")

    def bank_list_update(self, widget):
        """Updating bank data information"""
        status, message = chk_avail_update()
        if not status:
            infodial(self, message)
        elif questdial(self, message):
            error_info = bank_list_update()
            if error_info is None:
                infodial(
                    self,
                    _('Informacje o bankach zostały pomyślnie '
                      'uaktualnione.'))
            else:
                infodial(
                    self,
                    _('Nie udało się zaktualizować informacji o bankach:\n')
                    + error_info)

#-----------------------------------------------------------------------------#
def questdial(widget, t):
    res = False
    md = Gtk.MessageDialog(widget,
                           Gtk.DialogFlags.MODAL |
                           Gtk.DialogFlags.DESTROY_WITH_PARENT,
                           Gtk.MessageType.QUESTION,
                           Gtk.ButtonsType.YES_NO,
                           t)
    md.set_title(_("Pytanie"))
    r = md.run()
    if r == Gtk.ResponseType.YES:
        res = True
    md.destroy()
    return res
#-----------------------------------------------------------------------------#
def infodial(widget, t):
    md = Gtk.MessageDialog(widget,
                           Gtk.DialogFlags.MODAL |
                           Gtk.DialogFlags.DESTROY_WITH_PARENT,
                           Gtk.MessageType.INFO,
                           Gtk.ButtonsType.OK,
                           t)
    md.set_title(_("Informacja"))
    md.run()
    md.destroy()
#------------------------------------------------------------------------
if __name__ == "__main__":
    win = AppWindow()
    win.show_all()
    Gtk.main()
