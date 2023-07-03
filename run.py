from website import init_app, debug_mode

app = init_app()

if debug_mode and __name__ == "__main__":
    app.run(debug=True)