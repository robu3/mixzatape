import urwid

# StationSearchBox
# ================
# Basic edit box the emits `keypress` events.
class StationSearchBox(urwid.Edit):
	signals = ["change", "keypress"]

	def __init__(self, caption=u"", edit_text=u"", multiline=False,
            align="left", wrap="space", allow_tab=False,
            edit_pos=None, layout=None, mask=None):

		super(StationSearchBox, self).__init__(caption, edit_text, multiline, align, wrap, allow_tab, edit_pos, layout, mask)

	def keypress(self, size, key):
		self._emit("keypress", size, key)
		super(StationSearchBox, self).keypress(size, key)
