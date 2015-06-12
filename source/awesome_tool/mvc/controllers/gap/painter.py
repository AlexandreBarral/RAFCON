from gaphas.painter import HandlePainter

from cairo import ANTIALIAS_NONE


class MyHandlePainter(HandlePainter):

    def __init__(self, view=None):
        super(MyHandlePainter, self).__init__(view)

    def _draw_handles(self, item, cairo, opacity=None, inner=False):
        view = self.view
        cairo.save()
        i2v = view.get_matrix_i2v(item)
        if not opacity:
            opacity = (item is view.focused_item) and .7 or .4

        cairo.set_line_width(1)

        get_connection = view.canvas.get_connection
        for h in item.handles():
            if not h.visible:
                continue
            # connected and not being moved, see HandleTool.on_button_press
            if get_connection(h):
                r, g, b = 1, 0, 0
            # connected but being moved, see HandleTool.on_button_press
            elif get_connection(h):
                r, g, b = 1, 0.6, 0
            elif h.movable:
                r, g, b = 46./256., 154./256., 1
            else:
                r, g, b = 0, 0, 1

            cairo.identity_matrix()
            cairo.set_antialias(ANTIALIAS_NONE)
            cairo.translate(*i2v.transform_point(*h.pos))
            cairo.rectangle(-4, -4, 8, 8)
            if inner:
                cairo.rectangle(-3, -3, 6, 6)
            cairo.set_source_rgba(r, g, b, opacity)
            cairo.fill_preserve()
            if h.connectable:
                cairo.move_to(-2, -2)
                cairo.line_to(2, 3)
                cairo.move_to(2, -2)
                cairo.line_to(-2, 3)
            cairo.set_source_rgba(r/4., g/4., b/4., opacity*1.3)
            cairo.stroke()
        cairo.restore()