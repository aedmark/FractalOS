window.App = class App {
  constructor() {
    if (this.constructor === App) {
      throw new TypeError(
          'Abstract class "App" cannot be instantiated directly.'
      );
    }
    this.isActive = false;
    this.container = null;
  }

  enter(appLayer, options = {}) {
    throw new Error('Method "enter()" must be implemented.');
  }

  exit() {
    throw new Error('Method "exit()" must be implemented.');
  }

  handleKeyDown(event) {
    if (event.key === "Escape") {
      this.exit();
    }
  }
}
