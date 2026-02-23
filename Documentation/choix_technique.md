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