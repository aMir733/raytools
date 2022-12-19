from raytools.parser import Robot



updater = Updater(args.yaml["token"],use_context=True)
db = Database(db_path)
database = db.session()
