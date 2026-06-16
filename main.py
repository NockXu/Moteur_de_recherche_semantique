from ui.MainWindow import *

if __name__ == "__main__":
    import signal
    
    # Gérer Ctrl+C proprement
    def signal_handler(signum, frame):
        print(f"\n{tr('Interruption détectée, fermeture propre')}...")
        if 'window' in locals():
            # D'abord nettoyer, puis fermer
            QTimer.singleShot(0, window.cleanup)
            window.close()
        else:
            # Si la fenêtre n'existe pas encore, juste quitter
            app.quit()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Créer et afficher la fenêtre principale
    window = MainWindow()
    
    print(f"{tr('Application démarrée')}")
    print(f"{tr('Utilisez Ctrl+C pour fermer proprement')}")
    
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print(f"\n{tr('Au revoir')} !")