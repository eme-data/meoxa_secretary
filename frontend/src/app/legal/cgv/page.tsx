import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Conditions Générales de Vente — Secretary by Meoxa",
  description:
    "Conditions Générales de Vente du Pack Secrétariat de Secretary, édité par Meoxa.",
};

// ⚠️ Template de CGV à faire relire par un avocat avant usage en production.
// Les champs {{}} sont à compléter avec les informations société Meoxa.
export default function CgvPage() {
  return (
    <>
      <h1>Conditions Générales de Vente</h1>
      <p className="text-sm text-slate-400">
        Version 1.0 — en vigueur au {new Date().toLocaleDateString("fr-FR")}
      </p>

      <div className="my-6 rounded-lg border border-amber-800 bg-amber-900/20 p-4 text-sm text-amber-200">
        <strong>Note éditeur</strong> : ce document constitue une base. À faire valider
        par un conseil juridique avant publication pour un usage commercial.
      </div>

      <h2>Article 1 — Objet</h2>
      <p>
        Les présentes conditions générales de vente (« CGV ») ont pour objet de définir
        les conditions dans lesquelles <strong>Meoxa</strong>, {"{{FORME_JURIDIQUE}}"} au
        capital de {"{{CAPITAL}} €"}, immatriculée au RCS de {"{{VILLE_RCS}}"} sous le
        numéro {"{{SIREN}}"}, dont le siège social est situé{" "}
        {"{{ADRESSE_SIEGE}}"} (ci-après « l'Éditeur »), fournit l'application logicielle{" "}
        <strong>Secretary</strong> (ci-après « la Solution ») à des personnes morales
        professionnelles (ci-après « le Client »).
      </p>

      <h2>Article 2 — Acceptation des CGV</h2>
      <p>
        L'accès à la Solution implique l'acceptation pleine et entière des présentes
        CGV par le Client. L'acceptation est matérialisée par la création d'un compte
        et la souscription à un abonnement.
      </p>

      <h2>Article 3 — Description de la Solution</h2>
      <p>
        Secretary est une application SaaS d'automatisation du secrétariat,
        intégrée à Microsoft 365, permettant notamment :
      </p>
      <ul>
        <li>La génération automatique de brouillons de réponse aux emails</li>
        <li>La production de comptes-rendus de réunions Teams</li>
        <li>La proposition de créneaux d'agenda</li>
      </ul>
      <p>
        Secretary est un <strong>logiciel</strong>. Le traitement des données est
        entièrement automatisé ; aucun collaborateur de Meoxa ne consulte les données
        du Client dans le cadre normal de l'exploitation.
      </p>

      <h2>Article 4 — Tarifs et modalités de paiement</h2>
      <p>
        Le Pack Secrétariat est proposé au tarif de <strong>1 490 € HT par an</strong>,
        payable d'avance par prélèvement ou carte bancaire via Stripe. Le tarif
        s'entend pour un nombre illimité d'utilisateurs au sein d'une même organisation.
      </p>
      <p>
        L'abonnement est <strong>reconduit tacitement</strong> chaque année à date
        anniversaire, sauf résiliation par le Client dans les conditions prévues à
        l'article 7.
      </p>
      <p>
        Meoxa se réserve le droit de modifier ses tarifs à tout moment. Toute
        modification sera notifiée au Client par email au moins 30 jours avant son
        entrée en vigueur et ne s'appliquera qu'au prochain renouvellement.
      </p>

      <h2>Article 5 — Durée</h2>
      <p>
        L'abonnement prend effet à la date de souscription et est conclu pour une
        durée de 12 mois renouvelable par tacite reconduction.
      </p>

      <h2>Article 6 — Obligations de l'Éditeur</h2>
      <p>L'Éditeur s'engage à :</p>
      <ul>
        <li>Mettre à disposition la Solution dans des conditions opérationnelles normales</li>
        <li>Assurer une disponibilité moyenne annuelle supérieure à 99 %</li>
        <li>Maintenir la sécurité et la confidentialité des données</li>
        <li>Fournir un support par email dans un délai ouvré</li>
      </ul>

      <h2>Article 7 — Résiliation</h2>
      <p>
        Le Client peut résilier son abonnement à tout moment depuis son espace de
        facturation. La résiliation prend effet à la fin de la période annuelle payée ;
        aucun remboursement prorata n'est effectué. Les données du Client restent
        exportables pendant 30 jours après la résiliation.
      </p>
      <p>
        L'Éditeur peut résilier le contrat en cas de manquement grave du Client,
        notamment d'usage contraire aux lois en vigueur ou de non-paiement.
      </p>

      <h2>Article 8 — Limitation de responsabilité</h2>
      <p>
        La Solution est fournie « en l'état ». La responsabilité de l'Éditeur est
        limitée au montant de l'abonnement payé sur les 12 derniers mois. L'Éditeur
        ne saurait être tenu responsable des conséquences indirectes de l'utilisation
        de la Solution (perte de données, perte d'exploitation, manque à gagner).
      </p>
      <p>
        Le Client conserve la responsabilité pleine et entière du contenu des
        brouillons d'emails envoyés, des comptes-rendus diffusés et des décisions
        prises à partir des sorties produites par la Solution.
      </p>

      <h2>Article 9 — Données personnelles</h2>
      <p>
        Le traitement des données personnelles dans le cadre de la Solution est régi
        par notre <a href="/legal/confidentialite">Politique de confidentialité</a>.
        Un contrat de sous-traitance RGPD (DPA) est disponible sur demande et
        généré automatiquement depuis l'espace administration du Client.
      </p>

      <h2>Article 10 — Propriété intellectuelle</h2>
      <p>
        L'Éditeur concède au Client une licence d'utilisation non-exclusive et
        non-cessible de la Solution pour la durée de l'abonnement. Toute propriété
        intellectuelle sur la Solution reste celle de l'Éditeur.
      </p>
      <p>
        Les données du Client demeurent sa propriété exclusive. L'Éditeur ne les
        utilise pas pour entraîner de modèles d'intelligence artificielle.
      </p>

      <h2>Article 11 — Force majeure</h2>
      <p>
        Aucune des parties ne peut être tenue pour responsable d'un manquement à
        ses obligations résultant d'un cas de force majeure au sens de l'article 1218
        du Code civil.
      </p>

      <h2>Article 12 — Droit applicable et juridiction</h2>
      <p>
        Les présentes CGV sont soumises au droit français. Tout litige est de la
        compétence exclusive des tribunaux de {"{{VILLE_TRIBUNAL}}"}, nonobstant
        pluralité de défendeurs ou appel en garantie.
      </p>

      <h2>Article 13 — Contact</h2>
      <p>
        Pour toute question relative aux présentes CGV :{" "}
        <a href="mailto:contact@meoxa.app">contact@meoxa.app</a>.
      </p>
    </>
  );
}
