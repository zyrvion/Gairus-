# Accès Gaïrus et ZAREL sur le domaine Zyrvion

## Périmètre demandé et état vérifié

Le 30 octobre 2026, le Fondateur a demandé cette répartition :

| Adresse | Destination | État du raccordement |
| --- | --- | --- |
| `zyrvion.io` et `www.zyrvion.io` | Application Zyrvion existante | À préserver sans modification |
| `gairus.zyrvion.io` | Redirection gratuite vers le moteur Gaïrus chez Hugging Face | CNAME créé, certificat HTTPS encore en attente |
| `zarel.zyrvion.io` | ZAREL, application distincte | DNS non configuré, hébergement stable et protection d'accès à vérifier |

Le contrôle initial auprès du serveur DNS autoritatif Spaceship
`launch1.spaceship.net` retournait `NXDOMAIN` pour les deux nouveaux
sous-domaines. Après intervention, il retourne `gairus.zyrvion.io CNAME
zyrvion.github.io` avec un TTL de 1 800 secondes. ZAREL n'a pas été raccordé.
L'adresse principale pointe toujours vers `76.76.21.21` et
`www` vers `cname.vercel-dns.com`. La configuration du dépôt Zyrvion existant
confirme un déploiement Vercel, avec Convex pour le backend.
Cela explique le montage antérieur : l'application est déployée séparément,
puis son nom de domaine est raccordé au déploiement. Ce constat ne démontre pas
l'existence d'un VPS acheté avec le domaine.

Le 30 octobre, après autorisation du propriétaire d'utiliser ses e-mails pour
les connexions, l'accès au gestionnaire Spaceship a été ouvert et la zone
complète de douze enregistrements a été sauvegardée en privé. Aucune clé API
supplémentaire n'est nécessaire pour cette intervention par le gestionnaire.
Le site GitHub Pages a été associé au nom Gaïrus avant l'ajout de son CNAME.
La zone relue contient treize enregistrements ; une comparaison structurée
confirme que les douze entrées antérieures, valeurs, priorités et TTL compris,
sont inchangées. La page répond en HTTP 200 ; le certificat personnalisé
HTTPS n'est pas encore émis et ne doit pas être présenté comme opérationnel.
Aucun serveur de noms n'a été changé et aucune formule payante n'a été activée.

## Gaïrus : point d'accès gratuit

Le moteur reste chez Hugging Face. Le budget demeure nul.
Un domaine personnalisé directement attaché au Space requiert une formule
payante, qui n'est pas autorisée
([conditions Hugging Face](https://huggingface.co/docs/hub/spaces-custom-domain)).

Le dépôt Gairus est public. GitHub Pages peut servir `docs/index.html` depuis
la branche de correction, sans fusionner `main`, sans nouveau compte ni paiement.
Cette page redirige vers `https://nostraempire-gairus.hf.space`.
Elle n'est pas le serveur d'inférence, un proxy authentifié ou un hébergement
de données personnelles.

### Raccordement par les comptes existants

- Contrôler le domaine dans le compte Spaceship du propriétaire et sauvegarder
  la zone avant toute modification. Une vérification de domaine supplémentaire
  au niveau du compte GitHub reste recommandée lorsqu'elle est disponible.
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
pas l'adresse Hugging Face après ouverture. Le fichier `docs/CNAME` réserve
le nom demandé au site Pages de cette branche. L'état final de résolution et
du certificat doit être vérifié séparément et consigné avant de présenter
le sous-domaine comme opérationnel.

## ZAREL : ne pas confondre lien temporaire et hébergement permanent

Le stockage privé du propriétaire contient des données et des adaptateurs ZAREL.
L'interface Gradio indiquée dans ce stockage est accessible au contrôle du
30 octobre, avec texte et pièces jointes. Aucun message de test n'a été envoyé,
aucune conversation n'a été modifiée et aucun entraînement n'a été relancé.

Cette interface utilise un lien temporaire lié à une séance Kaggle, pas un
hébergement permanent vérifié. Aucun écran de connexion n'a été présenté
au contrôle anonyme. Il ne faut donc pas la présenter comme un accès privé
authentifié, ni publier son adresse temporaire dans ce dépôt public.

Avant de raccorder `zarel.zyrvion.io` :

- Retrouver le code de déploiement et le mode de relance de ZAREL sans
  interrompre la séance ni les travaux d'entraînement existants.
- Choisir ou vérifier un hébergement compatible avec le budget nul, sans
  achat, ajout de carte, crédit prépayé ou bascule payante implicite.
- Protéger l'accès au serveur et aux données du Fondateur ; une adresse
  difficile à deviner ne remplace pas une authentification.
- Vérifier une destination opérationnelle et un certificat HTTPS avant
  d'ajouter son nom DNS. Ne pas pointer vers le seul dépôt des poids ou
  vers une page factice.
- Garder la mémoire, les données d'entraînement et les accès ZAREL séparés
  de ceux de Gaïrus et de l'application Zyrvion.

Un nom DNS stable ne rend pas permanente une séance de calcul temporaire.
Le raccordement au domaine et l'hébergement continu sont deux vérifications
distinctes ; aucune disponibilité permanente n'est affirmée ici.

## Accès Spaceship et garde-fous

L'[API officielle Spaceship](https://docs.spaceship.dev/) utilise
`https://spaceship.dev/api` et les deux en-têtes `X-API-Key` et `X-API-Secret`.
Demander uniquement `dnsrecords:read` et `dnsrecords:write`. Les valeurs restent
dans le formulaire sécurisé, jamais dans Slack, ce dépôt ou une commande.

L'API est facultative : l'accès au gestionnaire authentifié permet également
l'intervention autorisée, sans création de nouvelles clés. Dans les deux cas :

- Lire la zone complète, avec pagination, et en conserver une sauvegarde privée.
- Vérifier les entrées et conflits des seuls noms explicitement concernés.
- Préserver apex, `www`, MX, SPF, DKIM, DMARC et toutes les autres entrées.
- Ne pas utiliser `force: true`, ne pas changer de serveurs DNS et ne pas
  remplacer aveuglément la zone complète.
- Ajouter uniquement les entrées nécessaires aux deux sous-domaines et à
  la preuve de propriété du domaine, puis relire la zone pour vérifier que
  les entrées préexistantes n'ont pas changé.
- Vérifier la résolution auprès des serveurs autoritatifs, le certificat,
  l'ouverture réelle de chaque application et les contrôles d'accès.

Le formulaire DNS ne constitue pas une autorisation de modifier les autres
produits Spaceship ni de souscrire un hébergement.
