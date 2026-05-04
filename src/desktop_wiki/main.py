from desktop_wiki.core.wiki_domain import WikiDB
from desktop_wiki.ui.wiki_ui import WikiUI
from desktop_wiki.services.wiki_service import WikiService

import sys
import logging
from PyQt6.QtWidgets import QApplication, QMessageBox


logger = logging.getLogger(__name__)


def setup_logging():
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
        )


def main():
    setup_logging()
    logger.info("Starting Wiki application...")

    app = None  # 🔥 garante que existe referência clara

    try:
        # 1️⃣ PRIMEIRO: QApplication (OBRIGATÓRIO ANTES DE QUALQUER UI)
        logger.info("Starting Qt application...")
        app = QApplication(sys.argv)

        # 2️⃣ depois lógica da aplicação
        logger.info("Initializing database...")
        db = WikiDB()

        logger.info("Initializing service layer...")
        service = WikiService(db)

        # 3️⃣ UI
        window = WikiUI(service=service)
        window.show()

        logger.info("Application started successfully.")

        sys.exit(app.exec())

    except Exception as e:
        logger.exception("Fatal error starting application")

        # garante app existente
        if QApplication.instance() is None:
            app = QApplication(sys.argv)

        QMessageBox.critical(
            None,
            "Error starting application",
            f"An unexpected error occurred:\n\n{str(e)}"
        )

        sys.exit(1)


if __name__ == "__main__":
    main()