import pickle
import pandas as pd
from typing import Tuple, List
from configs.paths import DataPaths


def inOutkeys_to_lists(df: pd.DataFrame) -> Tuple[List[str], List[str]]:
    """
    Splits 'inOutkey' column of a dataframe into two lists.

    Args:
        df (pd.DataFrame): Input dataframe which contains 'inOutkey' column.

    Returns:
        Tuple[List[str], List[str]]: Two lists representing the first and second IDs.
    """

    first_ids = []
    second_ids = []
    df['inOutkey'] = df['inOutkey'].apply(lambda x: x.replace('[', '').replace(']', ''))
    for item in df['inOutkey'].tolist():
        x = item.split(',')
        first_ids.append(x[0].strip())
        second_ids.append(x[1].strip())

    return first_ids, second_ids


def convert_object_to_category(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts all object type columns in a dataframe into category type.

    Args:
        df (pd.DataFrame): Input dataframe.

    Returns:
        pd.DataFrame: Dataframe with object type columns converted to category type.
    """

    df_obj = df.select_dtypes(['object'])
    for col in list(df_obj.columns):
        df[col] = df[col].apply(lambda x: str(x).strip())
        df[col] = df[col].astype('category')
    return df


def create_header_file(cols: List[str], header_path) -> None:
    """
    Creates a header file.

    Args:
        cols (List[str]): List of column names.
        header_path (str): Path where the header file will be saved.
    """

    df_headers = pd.DataFrame(columns=cols)
    df_headers.to_csv(header_path, sep='|', index=False)


class DataProcessor:
    def __init__(self) -> None:
        """
        Initialize the DataProcessor object, setting up paths.
        """

        self.paths = DataPaths()

    def process_directional_rels(self) -> None:
        """
        Process directional relationships from raw data and save it as a pickle file.
        """

        output_path = self.paths.get_full_path(self.paths.directional_rels_procd)
        df = pd.read_csv(self.paths.get_full_path(self.paths.directional_rels), sep='|', header=None, encoding='utf-8')
        df.columns = ['msrc_id', ':START_ID', 'type:TYPE', 'effect', 'mechanism', 'ref_count:int', 'sent_count:int', ':END_ID',
                      'id2', 'biomarkertype', 'celllinename', 'celltype', 'changetype', 'organ', 'organism',
                      'quantitativetype', 'tissue', 'nct_id', 'phase']
        df = df.drop(columns=['id2'])
        df['phase'] = df['phase'].fillna('None')
        df = convert_object_to_category(df)
        df['ref_count:int'] = df['ref_count:int'].astype('int16')
        df['sent_count:int'] = df['sent_count:int'].astype('int16')
        with open(output_path, 'wb') as file:
            pickle.dump(df, file)

    def process_bi_directional_rels(self) -> None:
        """
        Process bidirectional relationships from raw data and save it as a pickle file.
        """

        output_path = self.paths.get_full_path(self.paths.bidirectional_rels_procd)

        df = pd.read_csv(self.paths.get_full_path(self.paths.bidirectional_rels), sep='|', header=None,
                         encoding='utf-8')
        df.columns = ['msrc_id', ':START_ID', 'inOutkey', 'type:TYPE', 'relationship', 'effect', 'mechanism',
                      'ref_count:int', 'sent_count:int', ':END_ID', 'id2', 'biomarkertype', 'celllinename', 'celltype',
                      'changetype', 'organ', 'organism', 'quantitativetype', 'tissue']
        first_ids, second_ids = inOutkeys_to_lists(df)
        df.drop(columns=['inOutkey', 'id2', 'relationship'], inplace=True)
        df[':START_ID'] = first_ids
        df[':END_ID'] = second_ids
        df[':START_ID'] = df[':START_ID'].astype('int64')
        df[':END_ID'] = df[':END_ID'].astype('int64')
        df['ref_count:int'] = df['ref_count:int'].astype('int16')
        df['sent_count:int'] = df['sent_count:int'].astype('int16')
        df = convert_object_to_category(df)
        with open(output_path, 'wb') as file:
            pickle.dump(df, file)

    def process_attribute_rels(self) -> None:
        """
        Process attribute relationships from raw data and save it as a pickle file.
        """

        output_path = self.paths.get_full_path(self.paths.attribute_rels_procd)
        df = pd.read_csv(self.paths.get_full_path(self.paths.attribute_rels), sep='|', header=None, encoding='utf-8',
                         low_memory=False)
        df.columns = ['msrc_id', ':START_ID', 'id2', 'type:TYPE', ':END_ID']
        df = df.drop(columns=['id2'])
        df = df.dropna(how='any')
        df.reset_index(drop=True, inplace=True)
        for col in list(df.columns):
            df[col] = df[col].apply(lambda x: str(x).strip())
        df[':START_ID'] = pd.to_numeric(df[':START_ID'], errors='coerce').astype('int64')
        df[':END_ID'] = pd.to_numeric(df[':END_ID'], errors='coerce').astype('int64')
        df['type:TYPE'] = df['type:TYPE'].astype('category')
        df['type:TYPE'] = df['type:TYPE'].str.replace('-', '_')
        with open(output_path, 'wb') as file:
            pickle.dump(df, file)

    def concat_relationship_files(self) -> None:
        """
       Concatenate processed relationship dataframes and save to a file.
       """
        output_path = self.paths.get_full_path(self.paths.concat_relationships_procd)

        df_directional = pd.read_pickle(self.paths.get_full_path(self.paths.directional_rels_procd))
        df_biDirectional = pd.read_pickle(self.paths.get_full_path(self.paths.bidirectional_rels_procd))
        df_att = pd.read_pickle(self.paths.get_full_path(self.paths.attribute_rels_procd))

        df_concat = pd.concat([df_directional, df_biDirectional, df_att], ignore_index=True)
        df_concat['ref_count:int'].fillna(0, inplace=True)
        df_concat['sent_count:int'].fillna(0, inplace=True)
        for col in df_concat.select_dtypes(include=['category']).columns:
            df_concat[col] = df_concat[col].astype('object')
        df_concat.fillna('None', inplace=True)
        df_concat = df_concat.replace('nan', 'None')
        df_concat = df_concat.replace('None', '_')

        df_concat['ref_count:int'] = df_concat['ref_count:int'].astype('int16')
        df_concat['sent_count:int'] = df_concat['sent_count:int'].astype('int16')
        df_concat['msrc_id'] = df_concat['msrc_id'].astype('int64')
        df_concat = convert_object_to_category(df_concat.drop_duplicates().reset_index(drop=True))

        df_concat['type:TYPE'] = df_concat['type:TYPE'].apply(lambda x: x.upper())
        cols = list(df_directional.columns)
        df_concat[cols].to_csv(output_path, sep='|', index=False, header=False)

        header_path = self.paths.get_full_path(self.paths.relationships_header)
        create_header_file(cols, header_path)

    def process_node_file(self) -> None:
        """
        Process node data from raw data and save it to a file.
        """
        output_path = self.paths.get_full_path(self.paths.nodes_procd)
        df = pd.read_csv(self.paths.get_full_path(self.paths.nodes_raw), sep='|', header=None, encoding='utf-8',
                         low_memory=False)
        df.columns = [':ID', 'postgresqlID', 'name', ':LABEL', 'urn', 'alias', 'description','notes','reaxysID','casID']
        df = df.applymap(lambda x: str(x).strip())
        df[':LABEL'] = df[':LABEL'].apply(lambda x: x.upper())
        df[':ID'] = df[':ID'].astype('int64')
        df['name'] = df['name'].replace([';;', ';'], ':', regex=True)

        df.fillna('None', inplace=True)
        df.replace('nan', 'None', inplace=True) 
        df.replace('None', '_', inplace=True)

        df.to_csv(output_path, sep='|', index=False, header=False)
        cols = list(df.columns)
        header_path = self.paths.get_full_path(self.paths.nodes_header)
        create_header_file(cols, header_path)
