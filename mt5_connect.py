import Metatrader5 as mt5

def connect():
    if not mt5.initialize():
        print("Connexion échouée")
        return False
    return True

def shutdown():
    mt5.shutdown