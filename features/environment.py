import glob

def before_all(context):
    context.identities = sorted(glob.glob("features/certificates/player-*.pem"))
    context.trusted = sorted(glob.glob("features/certificates/player-*.cert"))
