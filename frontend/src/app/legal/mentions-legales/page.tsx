import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Mentions légales — Secretary by Meoxa",
  description: "Informations légales concernant Secretary, application éditée par Meoxa.",
};

// ⚠️ À COMPLÉTER par le client avant publication : les champs entre {{}} doivent
// être remplacés par les informations légales réelles de la société Meoxa.
export default function MentionsLegalesPage() {
  return (
    <>
      <h1>Mentions légales</h1>
      <p className="text-sm text-slate-400">Dernière mise à jour : avril 2026</p>

      <h2>1. Éditeur du site</h2>
      <p>
        Le site <strong>secretary.meoxa.app</strong> et l'application{" "}
        <strong>Secretary</strong> sont édités par :
      </p>
      <ul>
        <li><strong>Meoxa</strong> — {"{{FORME_JURIDIQUE}}"} au capital de {"{{CAPITAL}} €"}</li>
        <li>Siège social : {"{{ADRESSE_COMPLETE}}"}</li>
        <li>RCS {"{{VILLE_RCS}}"} — SIREN {"{{NUMERO_SIREN}}"}</li>
        <li>TVA intracommunautaire : {"{{TVA_INTRA}}"}</li>
        <li>Directeur de la publication : {"{{NOM_DIRECTEUR}}"}</li>
        <li>Email : <a href="mailto:contact@meoxa.app">contact@meoxa.app</a></li>
      </ul>

      <h2>2. Hébergeur</h2>
      <p>
        Le site et l'application sont hébergés par <strong>{"{{NOM_HEBERGEUR}}"}</strong>,
        {"{{FORME_HEBERGEUR}}"} enregistrée sous le numéro {"{{SIREN_HEBERGEUR}}"},
        dont le siège est situé {"{{ADRESSE_HEBERGEUR}}"}.
      </p>
      <p>
        Les serveurs sont localisés en <strong>Union européenne</strong>, en conformité
        avec l'article 44 du RGPD.
      </p>

      <h2>3. Propriété intellectuelle</h2>
      <p>
        L'ensemble des éléments présents sur le site et dans l'application Secretary
        (textes, graphismes, logos, code source, base de données) est la propriété
        exclusive de Meoxa ou de ses partenaires, protégée par le Code de la propriété
        intellectuelle. Toute reproduction, représentation, modification, publication,
        adaptation, totale ou partielle, sous quelque forme que ce soit, est interdite
        sans autorisation écrite préalable de Meoxa.
      </p>

      <h2>4. Données personnelles</h2>
      <p>
        Le traitement des données personnelles effectué dans le cadre de Secretary est
        détaillé dans notre <a href="/legal/confidentialite">Politique de confidentialité</a>.
      </p>

      <h2>5. Cookies</h2>
      <p>
        L'utilisation de cookies est détaillée dans notre{" "}
        <a href="/legal/cookies">Charte cookies</a>.
      </p>

      <h2>6. Droit applicable</h2>
      <p>
        Les présentes mentions légales sont soumises au droit français. Tout litige
        relatif à leur interprétation ou exécution relèvera de la compétence exclusive
        des tribunaux de {"{{VILLE_TRIBUNAL}}"}.
      </p>

      <h2>7. Contact</h2>
      <p>
        Pour toute question relative au site ou à l'application, écris-nous à{" "}
        <a href="mailto:contact@meoxa.app">contact@meoxa.app</a>.
      </p>
    </>
  );
}
