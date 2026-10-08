"""Annual species counts from the reports and retained dataset."""

import pandas as pd


def compare_report_totals(observations, reference, mappings):
    records = observations[observations['use_for_counts']].assign(year=observations['date'].dt.year)
    mappings = mappings.assign(taxon_name_original=mappings['dataset_taxa'].str.split('|')).explode('taxon_name_original')
    mappings = mappings.rename(columns={'dataset_source': 'source'})[['species', 'source', 'taxon_name_original']].drop_duplicates()
    counts = records.merge(mappings, on=['source', 'taxon_name_original']).groupby(['year', 'species'])['count'].sum()
    coverage = records[['source', 'year']].drop_duplicates().merge(mappings[['species', 'source']].drop_duplicates(), on='source')
    index = pd.MultiIndex.from_frame(coverage[['year', 'species']].drop_duplicates())
    counts = counts.reindex(index, fill_value=0).rename('dataset_count').reset_index()
    return reference.rename(columns={'count': 'report_count'}).merge(counts, on=['year', 'species'], how='outer').sort_values(['year', 'species']).astype({'report_count': 'Int64', 'dataset_count': 'Int64'})
