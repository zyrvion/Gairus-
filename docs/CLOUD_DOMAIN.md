# Accès Gaïrus sur le domaine Zyrvion

Le moteur reste chez Hugging Face. Le budget demeure nul.
Un domaine personnalisé directement attaché au Space requiert une formule
payante, qui n'est pas autorisée
([conditions Hugging Face](https://huggingface.co/docs/hub/spaces-custom-domain)).

## Point d'accès gratuit

Le dépôt Gairus est public. GitHub Pages peut servir `docs/index.html` depuis
la branche de correction, sans fusionner `main`, sans nouveau compte ni paiement.
Cette page redirige vers `https://nostraempire-gairus.hf.space`.
Elle n'est pas le serveur d'inférence, un proxy authentifié ou un hébergement
de données personnelles.

## Raccordement à effectuer après obtention de l'accès DNS

- Vérifier la propriété du domaine dans le compte GitHub avant l'association.
- Associer `gairus.zyrvion.io` à ce site Pages.
- Ensuite seulement, ajouter le CNAME `gairus` vers `zyrvion.github.io`,
  sans nom de dépôt dans la cible.
- Préserver intégralement apex, `www`, MX, SPF, DKIM et DMARC.
- Attendre le certificat puis vérifier HTTPS et la redirection réelle.
- Ne pas ajouter de wildcard et ne jamais laisser de CNAME pointant vers
  un site Pages supprimé.

Ces règles suivent la
[documentation GitHub sur les domaines personnalisés](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site).
Cette solution fournit une adresse d'accès qui redirige ; elle ne masque
pas l'adresse Hugging Face après ouverture. Le DNS n'est pas configuré
tant que l'accès au gestionnaire du domaine n'a pas été obtenu.
