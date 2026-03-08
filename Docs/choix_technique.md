## Config de Njango et et creation de .env

Après avoir rajoute les dépendances de requierements.txt nous 

 installons et paramétrons le projet avec

```powershell
 django-admin startproject core . 
```

on segment de la production du local pour les données de la base  

nous paramétrons les variables d’environnement 

nous installons l’application avec 

```powershell
 django-admin startapp _app     
```

nous migrons les donnees raw csv apres les avoir transforme

## Création des Models

étant donne que nous nous basons sur les csv existant nous créons les models fonction de chaque dataset 

pour permettre la description d’entête de chaque model nous utilisons `db_comment=`

on utilse la 

`class Meta:` pour prendre un peu plus de control sur la façon que ndango va migrer nos table le nom ,l’ordre…

pour faciliter l’accès rapide lors de la recherche textuelle nous introduisons la variable `SearchVectorField`  nous n’allons pas entrer en profondeur dans son implémentation mais nous voulons mettre a disposition pour les equipe DEV afin d’implémenter une logique métier selon le besoin

de meme nous introduisons `PointField` notons que pour l’utiliser dans django il faudre changer son moteur de DATABASE 

`'ENGINE': 'django.contrib.gis.db.backends.postgis'`

### Importance de PointField sur PostgreSQL

Le `PointField` est un type de champ particulièrement puissant dans Django lorsqu'il est utilisé avec PostgreSQL, car il tire parti des capacités géospatiales avancées de PostGIS. 

**Avantages principaux :**

- **Stockage efficace des coordonnées géographiques :** Le `PointField` permet de stocker des coordonnées (latitude, longitude) de manière optimisée dans la base de données.
- **Requêtes spatiales performantes :** PostgreSQL avec PostGIS offre des opérateurs spécialisés pour effectuer des requêtes géographiques complexes comme la recherche par proximité, le calcul de distances, ou la détermination de points dans un rayon donné.
- **Indexation spatiale :** Les index GiST (Generalized Search Tree) permettent d'accélérer considérablement les recherches géospatiales sur de grandes quantités de données.
- **Intégration native :** Django GIS s'intègre parfaitement avec PostgreSQL, permettant d'utiliser des méthodes comme `distance`, `dwithin`, ou `contains` directement dans les QuerySets.

Pour un projet e-commerce brésilien, cela devient particulièrement utile pour :

- Calculer les frais de livraison en fonction de la distance
- Trouver les points de retrait ou magasins les plus proches
- Optimiser les zones de livraison
- Analyser la distribution géographique des clients

## Commande importation CSV

pour pouvoir automatiser l’import des données et le remplissage automatique des models nous avons:

- Créer une commande Django pour faciliter l’accès étant dans tout le projet
- enrichi un peu plus de les CSV existent pour nous mettre en situation reel grâce a la bibliothèque `faker`
- nous avons paramétré la commande lui donnant accès au chemin des fichiers
- pour donner un aspect de chargement et voir la progressions des importation des données nous avons utilise la bibliothèque `tqdm` pour configurer on utilise
    
    ```powershell
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
        "file": {
            "class": "logging.FileHandler",
            "filename": "import.log",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    
    ```
    

## Problème lors de l’importation des csv

lors des test je me suis rendu compte que Django a besoin de vraies données pour tester les mock en clé étrangère ne pas pas

`FK Django → on a besoin d'une vraie Category en DB.MagicMock() est rejeté avec "must be a Category instance"`

du coup je cree une instance de categorie 

```python
    def setUp(self):
        self.cat      = make_category("perfumaria")
        self.fallback = Category.objects.create(
            product_category_name=UNCATEGORIZED_SLUG,
            product_category_name_english="Uncategorized",
        )
        self.cats = {
            "perfumaria":     self.cat,
            UNCATEGORIZED_SLUG: self.fallback,
        }
```

il faut noter que étant donne que dans produit il y avait 3 types de problème que j'ai fixer 

1. certain produit ont des catégories non existante
2. certain produit on la case catégories vide je créer une catégorie `Uncategorized`
3. certain sont bon

## Batch et Dry

### Pourquoi on utilise `batch_size` en Data Engineering

Un **batch** correspond au **nombre d’éléments traités en une fois**.

### Pourquoi on utilise `dry_run`

 permet **de tester le script sans faire de changements réels**

vérifier ce que le script va faire

 éviter de casser la base de données

 tester la logique

Sans modifier les données.

```python
if dry_run:
	print("User would be deleted:", user_id)
else:
	delete_user(user_id)
```

| Option | Rôle |
| --- | --- |
| `batch_size` | traiter les données par lot |
| `dry_run` | tester sans modifier |