from textual.app import App, ComposeResult
from textual.widgets import Header


class PinsApp(App):
    TITLE = "Pins Database"
    SUB_TITLE = "Store and analyze your bowling scores."

    def compose(self) -> ComposeResult:
        yield Header()


if __name__ == "__main__":
    app = PinsApp()
    reply = app.run()
    print(reply)
