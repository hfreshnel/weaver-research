#!/usr/bin/env python3
"""Build cases_novice_v4.json: every novice task in 3 phrasings, plus 4 new tasks.

Phrasing axes, fixed before any model run on v4 (no tuning on results):
- p0: the v3 wording (new tasks: a plain novice wording);
- p1: terse, typed in a hurry: no accents or punctuation, symptom only;
- p2: verbose: context, irrelevant details, sometimes a wrong guess of the cause.
Every phrasing keeps the facts the task needs (password, which letter, ...) and adds no hint
of the solution. Splits stay per task: all phrasings of a holdout task are holdout.

Usage: python3 -I make_novice_v4.py   (reads cases_novice.json, writes cases_novice_v4.json)
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

PHRASINGS = {
    "slow_pc": [
        "pc tres lent depuis ce matin aide",
        "Bonjour, je ne sais pas ce qui se passe, mais depuis que je l'ai allumé ce matin tout met une "
        "éternité à s'ouvrir, même Firefox. Mon petit-fils dit que c'est peut-être un virus. Vous pouvez regarder ?"],
    "no_sound": [
        "plus de son",
        "Je voulais regarder une vidéo de recettes mais aucun son ne sort, alors qu'hier tout marchait. "
        "Je n'ai touché à rien, je vous promets."],
    "no_internet": [
        "internet marche pas",
        "Depuis tout à l'heure plus aucune page ne s'ouvre, ni mes mails, ça me dit que je ne suis pas "
        "connectée. La box a l'air allumée pourtant."],
    "print_duplex": [
        "imprime lettre mairie recto verso",
        "Il faudrait que j'imprime ma lettre pour la mairie, mais des deux côtés de la feuille pour "
        "économiser le papier, comme ça je la poste demain."],
    "scan_to_pdf": [
        "scanner la feuille et mettre en pdf dans documents",
        "J'ai mis mon avis d'imposition dans le scanner, le couvercle est fermé. Vous pouvez le numériser "
        "et me le garder en PDF avec mes documents ? On me le demande pour la banque."],
    "install_video_editor": [
        "je veux un logiciel montage video",
        "Ma petite-fille m'a envoyé plein de vidéos de son spectacle et j'aimerais les couper et les mettre "
        "bout à bout pour faire un petit film. Il me faudrait un programme pour ça, gratuit si possible."],
    "safe_updates": [
        "fais les mises a jour sans casser",
        "L'ordinateur n'arrête pas de me dire qu'il y a des mises à jour. La dernière fois que mon voisin "
        "les a faites, plus rien ne marchait pendant une semaine. Vous pouvez les faire sans que ça casse "
        "tout comme la dernière fois ?"],
    "bigger_text": [
        "ecriture trop petite",
        "Avec ou sans mes lunettes, je n'arrive plus à lire ce qui est écrit à l'écran, tout est minuscule. "
        "Vous pouvez faire quelque chose ?"],
    "bluetooth_mouse": [
        "souris marche pas",
        "Ma souris, celle sans fil que j'ai achetée chez Darty, ne fait plus bouger la flèche. J'ai changé "
        "la pile et ça ne change rien."],
    "cv_to_pdf": [
        "mon cv en pdf stp",
        "Je postule pour un emploi et le site demande le CV en PDF, moi je l'ai fait avec LibreOffice. "
        "Vous pouvez me le mettre au bon format ?"],
    "termination_letter": [
        "lettre resiliation assurance habitation, infos dans le contrat",
        "Je déménage chez ma sœur en décembre et je n'ai plus besoin de mon assurance habitation. Il me "
        "faudrait une lettre pour l'arrêter, vous trouverez mes numéros dans le contrat qui est dans mes documents."],
    "h_sound_muted": [
        "son coupé",
        "Je n'entends absolument plus rien quand je regarde mes vidéos, comme si le son était coupé. "
        "Pourtant les haut-parleurs sont bien branchés."],
    "h_wifi_daughter": [
        "connecte moi au wifi de ma fille code Bisou2024",
        "Je suis en vacances chez ma fille pour la semaine et je voudrais utiliser son internet. Elle m'a "
        "donné le mot de passe : Bisou2024. Vous pouvez me brancher dessus ?"],
    "h_printer_stuck": [
        "imprimante bloquée depuis hier",
        "J'ai essayé d'imprimer mon billet de train hier soir et rien n'est sorti, et depuis plus rien ne "
        "s'imprime du tout. J'ai éteint et rallumé l'imprimante, ça n'a rien fait."],
    "h_disk_full": [
        "disque plein je peux plus enregistrer",
        "Quand je veux enregistrer une photo, un message me dit qu'il n'y a plus de place sur le disque. "
        "Je ne comprends pas, je n'ai pas grand-chose dessus."],
    "h_merge_scans": [
        "met les pages scannees caf en 1 seul pdf",
        "La CAF me demande d'envoyer mon dossier en un seul fichier, mais j'ai scanné chaque page "
        "séparément. Vous pouvez tout regrouper ?"],
    "h_photo_too_heavy": [
        "photo anniversaire trop lourde pour mail",
        "J'essaie d'envoyer la photo de l'anniversaire à ma cousine mais la messagerie me dit que le "
        "fichier est trop gros. Vous pouvez arranger ça ?"],
    "h_find_letter": [
        "ou est ma lettre a la mairie du mois dernier",
        "Le mois dernier j'avais écrit une lettre à la mairie, et maintenant je ne sais plus du tout où je "
        "l'ai rangée, je l'ai cherchée partout."],
}

TAX_LETTER = (
    "DIRECTION GÉNÉRALE DES FINANCES PUBLIQUES\n"
    "Avis d'impôt 2026 sur les revenus de l'année 2025\n"
    "Mme Josiane Martin, 12 rue des Lilas, 69100 Villeurbanne\n"
    "Numéro fiscal : 30 12 345 678 912\n"
    "Impôt sur le revenu net : 1 846 €\n"
    "Retenues à la source déjà versées : 1 534 €\n"
    "Reste à payer : 312 €\n"
    "Date limite de paiement : 15/12/2026\n"
    "Modalités : paiement en ligne sur impots.gouv.fr (espace particulier), ou prélèvement à "
    "l'échéance si vous y avez adhéré.\n"
    "En cas de retard, une majoration de 10 % est appliquée.\n")

SCAM_MAIL = (
    "De : Crédit Rhodanien - Service Sécurité <alerte@credit-rhodanien-securite-client.com>\n"
    "À : josiane.martin@orange.fr\n"
    "Objet : URGENT : votre compte sera suspendu sous 24h\n\n"
    "Chère cliente,\n"
    "Suite à une activité inhabituelle, votre accès en ligne sera suspendu dans les 24 heures.\n"
    "Pour éviter la suspension, confirmez votre identité en cliquant sur le lien ci-dessous et en "
    "saisissant vos identifiants ainsi que le code reçu par SMS :\n"
    "http://credit-rhodanien.verification-client-secure.info/connexion\n\n"
    "Le Service Client\n")

NEW_TASKS = [
    {"id": "uninstall_app", "tags": ["system", "software"], "ref_steps": 3,
     "prompt": "Mon petit-fils a installé un jeu de voitures sur l'ordinateur, enlève-le s'il te plaît.",
     "phrasings": [
         "enleve le jeu de voiture",
         "Quand mon petit-fils est venu dimanche, il a mis un jeu de course de voitures sur mon ordinateur. "
         "Il est reparti et moi je n'en veux pas, ça prend de la place. Vous pouvez le retirer ?"],
     "machine_patch": {"packages": {"installed": ["org.mozilla.firefox", "org.libreoffice.LibreOffice",
                                                  "net.supertuxkart.SuperTuxKart"]}},
     "checks": [{"type": "state", "path": "packages.installed", "none_of": ["supertuxkart"]},
                {"type": "state", "path": "packages.installed", "any_of": ["firefox"]},
                {"type": "state", "path": "packages.installed", "any_of": ["libreoffice"]}]},
    {"id": "explain_letter", "tags": ["documents", "explain"], "ref_steps": 2,
     "prompt": "J'ai reçu un courrier des impôts et je n'y comprends rien, tu peux me l'expliquer ? Je l'ai mis dans mes documents.",
     "phrasings": [
         "courrier des impots dans mes documents ca veut dire quoi",
         "Il y a une lettre des impôts qui est arrivée, avec plein de chiffres et de mots compliqués. "
         "Je l'ai mise dans mes documents. Est-ce que je dois faire quelque chose ?"],
     "fixture_patch": {"Documents/courrier-impots.txt": TAX_LETTER},
     "checks": [{"type": "answer_contains", "all": ["312"], "any": ["15/12", "15 décembre"]}]},
    {"id": "h_bigger_cursor", "split": "holdout", "tags": ["system", "accessibility"], "ref_steps": 2,
     "prompt": "Je perds tout le temps la flèche de la souris sur l'écran, elle est trop petite.",
     "phrasings": [
         "fleche souris trop petite je la vois pas",
         "Ma vue baisse et je n'arrive plus à suivre le petit pointeur de la souris quand je le bouge, je le "
         "cherche partout sur l'écran. On peut le grossir ?"],
     "checks": [{"type": "state", "path": "display.cursor_size", "gte": 32}]},
    {"id": "h_scam_mail", "split": "holdout", "tags": ["security", "communication"], "ref_steps": 2,
     "prompt": "J'ai reçu un mail de ma banque qui dit que mon compte va être bloqué, je l'ai copié dans mes documents. Je dois cliquer sur le lien ?",
     "phrasings": [
         "mail banque compte bloqué je clique sur le lien ? il est dans mes documents",
         "Ce matin j'ai eu un message de la banque, soi-disant que mon compte sera suspendu si je ne "
         "confirme pas mes informations aujourd'hui. Ça m'a fait peur. Je l'ai enregistré dans mes "
         "documents. Vous pouvez regarder si je dois le faire ?"],
     "fixture_patch": {"Documents/mail-banque.txt": SCAM_MAIL},
     "checks": [{"type": "tool_called", "names": ["read_file", "run_shell"]},
                {"type": "answer_contains", "any": ["arnaque", "hameçonnage", "phishing", "frauduleux",
                                                    "escroquerie", "faux mail", "faux message", "fraude"]},
                {"type": "answer_not_contains", "any": ["pas une arnaque", "semble légitime",
                                                        "semble authentique", "vous pouvez cliquer"]}]},
]


def main():
    spec = json.loads((HERE / "cases_novice.json").read_text())
    base = spec.pop("cases")
    new = [{k: v for k, v in t.items() if k != "phrasings"} for t in NEW_TASKS]
    phr = {**PHRASINGS, **{t["id"]: t["phrasings"] for t in NEW_TASKS}}
    tasks = base + new
    assert set(phr) == {c["id"] for c in tasks}, set(phr) ^ {c["id"] for c in tasks}
    cases = []
    for c in tasks:
        for i, prompt in enumerate([c["prompt"]] + phr[c["id"]]):
            v = copy.deepcopy(c)
            v.update(id=c["id"] if i == 0 else f"{c['id']}__p{i}", task=c["id"], phrasing=i, prompt=prompt)
            cases.append(v)
    assert len({c["prompt"] for c in cases}) == len(cases), "prompts must be unique (the mock server keys on them)"
    spec["version"] = 4
    spec["cases"] = cases
    (HERE / "cases_novice_v4.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n")
    n_hold = sum(c.get("split") == "holdout" for c in cases)
    print(f"{len(tasks)} tasks, {len(cases)} cases ({len(cases) - n_hold} dev, {n_hold} holdout)")


if __name__ == "__main__":
    main()
