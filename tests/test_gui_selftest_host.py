"""Dependency-free virtual GUI host contract."""

from unified.gui_selftest_host import install


def test_virtual_host_exercises_layout_callback_and_state():
    tk = install()
    root = tk.Tk()
    value = tk.StringVar(value="ready")
    events = []
    button = tk.Button(root, text="Run", command=lambda: events.append(value.get()))
    button.grid(row=2, column=3)

    selected = root.grid_slaves(row=2, column=3)[0]
    selected.invoke()

    assert selected.winfo_class() == "Button"
    assert selected.cget("text") == "Run"
    assert events == ["ready"]


def test_virtual_canvas_records_rendered_primitives():
    tk = install()
    canvas = tk.Canvas(tk.Tk())
    canvas.create_rectangle(0, 0, 10, 10)
    canvas.create_text(5, 5, text="score")

    assert len(canvas.find_all()) == 2
    canvas.delete("all")
    assert canvas.find_all() == ()
