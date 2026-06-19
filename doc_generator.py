from pathlib import Path

ROOT = Path(".")  # racine projet
DOCS = Path("documentation/Technique/")  # dossier mkdocs


def to_module(root: Path, file: Path) -> str:
    """Convertit un chemin fichier en module python.
    ex: models/index_repository.py -> models.index_repository
    """
    relative = file.with_suffix("")  # enlève .py
    parts = relative.parts
    return ".".join(parts)


def should_ignore(file: Path) -> bool:
    # Ignore si c'est un fichier __init__.py ou s'il y a "sam3" dans le chemin
    return "sam3" in file.parts or file.name == "__init__.py"


def format_title(name: str) -> str:
    """Formate le nom du fichier pour en faire un titre propre.
    ex: ollama_wrapper -> Ollama Wrapper
    """
    # Gère les cas particuliers si nécessaire, sinon fait une mise en forme standard
    words = name.replace("_", " ").split()
    return " ".join(word.capitalize() if not word.isupper() else word for word in words)


def generate_summary(processed_files: list[Path]) -> None:
    """Génère un fichier de sommaire Markdown basé sur les fichiers traités."""
    summary_path = DOCS / "sommaire_doc_technique.md"
    
    lines = ["# Documentation Technique\n", "## Sommaire\n"]
    
    # On trie les chemins pour avoir un ordre alphabétique logique
    processed_files.sort()
    
    current_section = None
    current_subsection = None
    
    for md_path in processed_files:
        # On récupère le chemin relatif par rapport au dossier DOCS
        # ex: ui/main_window.md ou common/image/image.md
        rel_to_docs = md_path.relative_to(DOCS)
        parts = rel_to_docs.parts
        
        # Le premier élément est toujours la section principale (ui, vision, common, database)
        section = parts[0].capitalize()
        
        # Si on change de section principale (ex: Vision -> Database)
        if section != current_section:
            current_section = section
            current_subsection = None  # Reset la sous-section
            lines.append(f"### {current_section}\n")
            
        # S'il y a des sous-dossiers (ex: common/image/image.md -> sous-dossier 'image')
        if len(parts) > 2:
            # On prend tous les sous-dossiers intermédiaires
            sub_folder_name = " ".join(parts[1:-1]).capitalize()
            subsection = f"Classes des {sub_folder_name}s" if not sub_folder_name.endswith('s') else f"Classes des {sub_folder_name}"
            
            if subsection != current_subsection:
                current_subsection = subsection
                lines.append(f"#### {current_subsection}\n")
        else:
            current_subsection = None

        # Formatage du nom du lien
        file_title = format_title(md_path.stem)
        
        # Le lien doit utiliser des slashs / même sous Windows
        link_url = rel_to_docs.as_posix()
        
        # Ajout de la ligne avec indentation si on est dans une sous-section
        indent = "" # Pas d'indentation nécessaire d'après votre exemple, mais modifiable si besoin
        lines.append(f"{indent}- [{file_title}]({link_url})")

    # Écriture du sommaire (écrase l'ancien pour être toujours à jour)
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n[SUCCESS] Sommaire généré avec succès dans : {summary_path}")


def main() -> None:
    target_directories = ["ui", "vision", "common", "database"]
    
    # Liste pour stocker tous les fichiers .md de la doc
    all_processed_markdowns = []

    for dir_name in target_directories:
        target_dir = ROOT / dir_name
        
        if not target_dir.exists():
            print(f"[WARNING] Le dossier ./{dir_name} n'existe pas, ignoré.")
            continue

        print(f"\n--- Analyse du dossier : {dir_name} ---")
        python_files = target_dir.rglob("*.py")

        for file in python_files:
            if should_ignore(file):
                continue

            module = to_module(ROOT, file)
            md_path = DOCS / file.with_suffix(".md")
            
            # On ajoute le fichier à notre liste pour le sommaire
            all_processed_markdowns.append(md_path)

            # création dossier si nécessaire
            md_path.parent.mkdir(parents=True, exist_ok=True)

            # contenu mkdocs
            content = f"::: {module}\n"

            # écrire seulement si fichier n'existe pas
            if not md_path.exists():
                md_path.write_text(content, encoding="utf-8")
                print(f"[CREATED] {md_path} -> {module}")
            else:
                print(f"[SKIP] {md_path} already exists")

    # Une fois tous les dossiers parcourus, on génère le sommaire
    if all_processed_markdowns:
        generate_summary(all_processed_markdowns)
    else:
        print("\n[INFO] Aucun fichier trouvé, sommaire non généré.")


if __name__ == "__main__":
    main()