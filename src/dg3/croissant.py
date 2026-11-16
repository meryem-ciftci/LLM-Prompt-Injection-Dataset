"""Croissant 1.0 (MLCommons) metadata for a G3 release, built only from its manifest.

Every number in the output is copied from the manifest written by ``write_release``;
nothing is estimated here.
"""
from __future__ import annotations

REPO_URL = "https://github.com/meryem-ciftci/LLM-Prompt-Injection-Dataset"
CONTEXT = {
    "@language": "en", "@vocab": "https://schema.org/", "sc": "https://schema.org/",
    "cr": "http://mlcommons.org/croissant/", "rai": "http://mlcommons.org/croissant/RAI/",
    "dct": "http://purl.org/dc/terms/", "citeAs": "cr:citeAs", "column": "cr:column",
    "conformsTo": "dct:conformsTo", "data": {"@id": "cr:data", "@type": "@json"},
    "dataType": {"@id": "cr:dataType", "@type": "@vocab"}, "examples": {"@id": "cr:examples", "@type": "@json"},
    "extract": "cr:extract", "field": "cr:field", "fileObject": "cr:fileObject", "fileProperty": "cr:fileProperty",
    "format": "cr:format", "includes": "cr:includes", "isLiveDataset": "cr:isLiveDataset",
    "jsonPath": "cr:jsonPath", "key": "cr:key", "md5": "cr:md5", "parentField": "cr:parentField",
    "path": "cr:path", "recordSet": "cr:recordSet", "references": "cr:references", "regex": "cr:regex",
    "repeated": "cr:repeated", "replace": "cr:replace", "separator": "cr:separator", "source": "cr:source",
    "subField": "cr:subField", "transform": "cr:transform",
}
FIELDS = (
    ("record_id", "sc:Text", "Stable record identifier."),
    ("family_id", "sc:Text", "Family of four records built from one carrier and one attack component."),
    ("family_role", "sc:Text", "clean | injected_untrusted | authorized_twin | trigger_benign."),
    ("label", "sc:Text", "Construction label: injection for injected_untrusted, otherwise benign."),
    ("language", "sc:Text", "Carrier language (en | tr)."),
    ("scenario", "sc:Text", "rag | document_qa."),
    ("split", "sc:Text", "train | validation | test (disjoint by article, family and attack component)."),
    ("carrier_text", "sc:Text", "Text shown to the model as untrusted or trusted content."),
    ("annotation_status", "sc:Text", "generated_candidate: deterministic assembly; no human review."),
    ("content_sha256", "sc:Text", "SHA-256 of carrier_text."),
)


def croissant(manifest: dict, *, name: str, description: str, version: str, file_url: str) -> dict:
    fields = [{"@type": "cr:Field", "@id": f"records/{key}", "name": key, "description": desc, "dataType": dtype,
               "source": {"fileObject": {"@id": "jsonl"}, "extract": {"column": key}}}
              for key, dtype, desc in FIELDS]
    return {
        "@context": CONTEXT,
        "@type": "sc:Dataset",
        "conformsTo": "http://mlcommons.org/croissant/1.0",
        "name": name,
        "description": description,
        "version": version,
        "license": "https://creativecommons.org/licenses/by-sa/4.0/",
        "url": REPO_URL,
        "isLiveDataset": False,
        "inLanguage": sorted(manifest["languages"]),
        "keywords": ["prompt injection", "indirect prompt injection", "LLM security", "Turkish", "English"],
        "distribution": [{
            "@type": "cr:FileObject", "@id": "jsonl", "name": manifest["canonical_file"],
            "contentUrl": file_url, "encodingFormat": "application/jsonlines", "sha256": manifest["sha256"],
        }],
        "recordSet": [{"@type": "cr:RecordSet", "@id": "records", "name": "records",
                       "description": f"{manifest['record_count']} records in {manifest['family_count']} families.",
                       "field": fields}],
        "rai:dataCollection": (
            "Carriers are paragraphs from SQuAD v1.1 dev (English Wikipedia) and pinned Turkish Wikipedia "
            "revisions, windowed to length buckets with real neighbouring text. Attack components were "
            "proposed by a local model and admitted only through automatic, independent quality control "
            "(rule checks plus a different local judge model). Records are assembled deterministically."),
        "rai:dataAnnotationProtocol": (
            "Labels are construction labels implied by the family role; no human annotation or human "
            "verification was performed. Automatic agreement between independent local models is "
            "reported separately when it has been run."),
        "rai:dataLimitations": (
            "Small pilot; attack components are model-generated and reused across families within a split; "
            "Turkish carriers have no reference answers (utility not measurable for tr); attack success "
            "rates are not part of this release."),
        "rai:dataUseCases": "Evaluating prompt-injection detectors and measuring attack success on target models.",
        "rai:personalSensitiveInformation": "None intended: all canaries, URLs and tool names are fictional.",
        "cr:dataStatistics": {k: manifest[k] for k in ("record_count", "family_count", "labels", "family_roles",
                                                        "languages", "scenarios", "splits")},
    }
