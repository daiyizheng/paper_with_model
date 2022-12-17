# -*- encoding: utf-8 -*-
'''
Filename         :pdb_complex_split.py
Description      :
Time             :2022/12/14 00:53:47
Author           :daiyizheng
Email            :387942239@qq.com
Version          :1.0
'''



import os
import sys
from prody import *
import pandas as pd
from rdkit import Chem
from rdkit.Chem import AllChem
from io import StringIO
import requests


def read_ligand_expo():
    """
    Read Ligand Expo data, try to find a file called
    Components-smiles-stereo-oe.smi in the current directory.
    If you can't find the file, grab it from the RCSB
    :return: Ligand Expo as a dictionary with ligand id as the key
    """
    file_name = "Components-smiles-stereo-oe.smi"
    try:
        df = pd.read_csv(file_name, sep="\t",
                         header=None,
                         names=["SMILES", "ID", "Name"])
    except FileNotFoundError:
        url = f"http://ligand-expo.rcsb.org/dictionaries/{file_name}"
        print(url)
        r = requests.get(url, allow_redirects=True)
        open('Components-smiles-stereo-oe.smi', 'wb').write(r.content)
        df = pd.read_csv(file_name, sep="\t",
                         header=None,
                         names=["SMILES", "ID", "Name"])
    df.set_index("ID", inplace=True)
    return df.to_dict()


def get_pdb_components(pdb_id):
    """
    Split a protein-ligand pdb into protein and ligand components
    :param pdb_id:
    :return:
    """
    pdb = parsePDB(pdb_id)
    protein = pdb.select('protein')
    ligand = pdb.select('not protein and not water')
    return protein, ligand


def process_ligand(ligand, res_name, expo_dict):
    """
    Add bond orders to a pdb ligand
    1. Select the ligand component with name "res_name"
    2. Get the corresponding SMILES from the Ligand Expo dictionary
    3. Create a template molecule from the SMILES in step 2
    4. Write the PDB file to a stream
    5. Read the stream into an RDKit molecule
    6. Assign the bond orders from the template from step 3
    :param ligand: ligand as generated by prody
    :param res_name: residue name of ligand to extract
    :param expo_dict: dictionary with LigandExpo
    :return: molecule with bond orders assigned
    """
    output = StringIO()
    sub_mol = ligand.select(f"resname {res_name}")
    sub_smiles = expo_dict['SMILES'][res_name]
    template = AllChem.MolFromSmiles(sub_smiles)
    writePDBStream(output, sub_mol)
    pdb_string = output.getvalue()
    rd_mol = AllChem.MolFromPDBBlock(pdb_string)
    new_mol = AllChem.AssignBondOrdersFromTemplate(template, rd_mol)
    return new_mol


def write_pdb(protein, pdb_name):
    """
    Write a prody protein to a pdb file
    :param protein: protein object from prody
    :param pdb_name: base name for the pdb file
    :return: None
    """
    pdb_name = os.path.splitext(pdb_name)[0]
    output_pdb_name = f"{pdb_name}_protein.pdb"
    writePDB(f"{output_pdb_name}", protein)
    print(f"wrote {output_pdb_name}")


def write_sdf(new_mol, pdb_name, res_name):
    """
    Write an RDKit molecule to an SD file
    :param new_mol:
    :param pdb_name:
    :param res_name:
    :return:
    """
    pdb_name = os.path.splitext(pdb_name)[0]
    outfile_name = f"{pdb_name}_{res_name}_ligand.sdf"
    writer = Chem.SDWriter(f"{outfile_name}")
    writer.write(new_mol)
    print(f"wrote {outfile_name}")


def main(pdb_name):
    """
    Read Ligand Expo data, split pdb into protein and ligands,
    write protein pdb, write ligand sdf files
    :param pdb_name: id from the pdb, doesn't need to have an extension
    :return:
    """
    df_dict = read_ligand_expo()
    protein, ligand = get_pdb_components(pdb_name)
    write_pdb(protein, pdb_name)

    res_name_list = list(set(ligand.getResnames()))
    for res in res_name_list:
        new_mol = process_ligand(ligand, res, df_dict)
        write_sdf(new_mol, pdb_name, res)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        print("Usage: {sys.argv[1]} pdb_id", file=sys.stderr)