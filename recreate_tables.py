import nudge.core.context


if __name__ == '__main__':
    ctx = nudge.core.context.NudgeCoreContext()

    with ctx.app.flask_app.app_context():
        ctx.db.recreate_tables()
