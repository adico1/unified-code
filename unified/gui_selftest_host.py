"""Dependency-free virtual GUI host for generated application self-tests."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock


def _variable(value=""):
    cell = [value]
    variable = MagicMock()
    variable.get.side_effect = lambda: cell[0]
    variable.set.side_effect = lambda selected: cell.__setitem__(0, selected)
    return variable


def _root():
    root = MagicMock()
    root._uc_root = root
    root._uc_grid = {}
    root._uc_children = []
    root.grid_slaves.side_effect = (
        lambda row=None, column=None: list(root._uc_grid.get((row, column), ()))
    )
    root.winfo_children.side_effect = lambda: list(root._uc_children)
    root.after.side_effect = lambda _delay, _operation: None
    return root


def _widget(kind, master=None, **options):
    widget = MagicMock()
    root = getattr(master, "_uc_root", master)
    widget._uc_root = root
    widget._uc_options = dict(options)
    widget._uc_value = ""
    widget._uc_items = []
    widget._uc_selection = []
    widget._uc_headings = {}
    widget._uc_tabs = []
    widget._uc_selected_tab = 0
    if root is not None and hasattr(root, "_uc_children"):
        root._uc_children.append(widget)

    def grid(**coordinates):
        if root is not None and hasattr(root, "_uc_grid"):
            key = (coordinates.get("row"), coordinates.get("column"))
            root._uc_grid.setdefault(key, []).append(widget)
        return widget

    def configure(**selected):
        widget._uc_options.update(selected)

    def insert(index, value, *values):
        if kind == "Treeview":
            identity = options.get("iid", str(len(widget._uc_items)))
            record = {"iid": identity, "values": values or value}
            widget._uc_items.append(record)
            return identity
        if kind in {"Listbox", "Notebook"}:
            widget._uc_items.append(value)
            return None
        widget._uc_value = str(value)
        return None

    def delete(*_coordinates):
        if kind in {"Canvas", "Listbox", "Treeview"}:
            widget._uc_items.clear()
            widget._uc_selection.clear()
        else:
            widget._uc_value = ""

    def get(*_coordinates):
        variable = widget._uc_options.get("textvariable")
        if variable is not None:
            return variable.get()
        return widget._uc_value

    def create(*_arguments, **_options):
        widget._uc_items.append(len(widget._uc_items) + 1)
        return widget._uc_items[-1]

    def invoke():
        command = widget._uc_options.get("command")
        return command() if command is not None else None

    def heading(identity, option=None, **selected):
        widget._uc_headings.setdefault(identity, {}).update(selected)
        return widget._uc_headings.get(identity, {}).get(option)

    def tree_insert(_parent, _index, iid=None, values=(), **_selected):
        identity = iid or str(len(widget._uc_items))
        widget._uc_items.append({"iid": identity, "values": values})
        return identity

    def selection_set(*identities):
        widget._uc_selection[:] = list(identities)

    def notebook_select(selected=None):
        if selected is not None:
            widget._uc_selected_tab = int(selected)
        return widget._uc_selected_tab

    widget.grid.side_effect = grid
    widget.pack.side_effect = lambda **_options: widget
    widget.configure.side_effect = configure
    widget.config.side_effect = configure
    widget.insert.side_effect = tree_insert if kind == "Treeview" else insert
    widget.delete.side_effect = delete
    widget.get.side_effect = get
    widget.invoke.side_effect = invoke
    widget.cget.side_effect = lambda identity: widget._uc_options.get(identity)
    widget.winfo_class.side_effect = lambda: kind
    widget.find_all.side_effect = lambda: tuple(widget._uc_items)
    widget.create_line.side_effect = create
    widget.create_rectangle.side_effect = create
    widget.create_oval.side_effect = create
    widget.create_text.side_effect = create
    widget.heading.side_effect = heading
    widget.column.side_effect = lambda *_args, **_kwargs: None
    widget.get_children.side_effect = lambda: tuple(
        item["iid"] for item in widget._uc_items
    )
    widget.selection.side_effect = lambda: tuple(widget._uc_selection)
    widget.selection_set.side_effect = selection_set
    widget.selection_remove.side_effect = lambda *_items: widget._uc_selection.clear()
    widget.curselection.side_effect = lambda: tuple(widget._uc_selection)
    widget.add.side_effect = lambda child, **_options: widget._uc_tabs.append(child)
    widget.select.side_effect = notebook_select
    widget.index.side_effect = lambda selected: int(selected)
    widget.__getitem__.side_effect = lambda identity: widget._uc_options.get(identity)
    return widget


def install():
    """Install the virtual host only in the current self-test process."""
    tkinter = ModuleType("tkinter")
    tkinter.__path__ = []
    tkinter.Tk = _root
    tkinter.StringVar = _variable
    for identity in (
        "Button",
        "Canvas",
        "Entry",
        "Frame",
        "Label",
        "Listbox",
        "Text",
    ):
        setattr(
            tkinter,
            identity,
            lambda master=None, _identity=identity, **options: _widget(
                _identity, master, **options
            ),
        )
    messagebox = ModuleType("tkinter.messagebox")
    messagebox.askyesno = lambda _title, _message: True
    ttk = ModuleType("tkinter.ttk")
    for identity in ("Notebook", "Scrollbar", "Treeview"):
        setattr(
            ttk,
            identity,
            lambda master=None, _identity=identity, **options: _widget(
                _identity, master, **options
            ),
        )
    sys.modules.update(
        {
            "tkinter": tkinter,
            "tkinter.messagebox": messagebox,
            "tkinter.ttk": ttk,
        }
    )
    return tkinter
