"""Prediction-time confidence allowlist; no reference-guided CSV columns accepted."""
import math

def finite_number(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        return None
    return float(value)

def native_features(model,payload,num_protein_chains,input_ligand_index):
    """Chain order must first be verified against each model's INPUT configuration.

    Raw confidence files are necessary but insufficient: an experimentally chosen
    ligand-chain index would still leak. Caller supplies a chemical identity match
    to an input ligand, never an experimental chain-assignment result.
    """
    if model not in ('protenix','boltz2'):raise ValueError('Unsupported predictor')
    if type(num_protein_chains) is not int or type(input_ligand_index) is not int or num_protein_chains<1 or input_ligand_index<0:raise ValueError('Invalid input chain indices')
    index=num_protein_chains+input_ligand_index
    return native_features_indices(model,payload,list(range(num_protein_chains)),index)

def native_features_indices(model,payload,protein_indices,ligand_index):
    """General form for input-verified chains, including interleaved cofactors."""
    if model not in ('protenix','boltz2'):raise ValueError('Unsupported predictor')
    if (not protein_indices or any(type(x) is not int or x<0 for x in protein_indices)
        or len(set(protein_indices))!=len(protein_indices) or type(ligand_index) is not int
        or ligand_index<0 or ligand_index in protein_indices):
        raise ValueError('Invalid or overlapping explicit confidence chain indices')
    index=ligand_index
    allowed={'protenix':{'ranking_score':'ranking_score','ptm':'ptm','iptm':'iptm','plddt':'plddt'},
             'boltz2':{'ranking_score':'confidence_score','ptm':'ptm','iptm':'iptm','complex_plddt':'complex_plddt','ligand_iptm':'ligand_iptm'}}
    features={name:finite_number(payload.get(key)) for name,key in allowed[model].items()}
    if model=='protenix':
        vector=payload.get('chain_plddt')
        if vector is None:features['input_ligand_chain_plddt']=None
        else:
            try:value=vector[str(index)] if isinstance(vector,dict) else vector[index]
            except (KeyError,IndexError,TypeError) as e:raise ValueError('Chain pLDDT incompatible with verified input chain order') from e
            features['input_ligand_chain_plddt']=finite_number(value)
    matrix=payload.get('chain_pair_iptm' if model=='protenix' else 'pair_chains_iptm')
    values=[]
    reverse=[]
    if matrix is not None:
        for protein_index in protein_indices:
            try:
                if isinstance(matrix,dict):
                    forward=matrix[str(protein_index)][str(index)]
                    backward=matrix[str(index)][str(protein_index)]
                else:
                    forward=matrix[protein_index][index]
                    backward=matrix[index][protein_index]
            except (IndexError,KeyError,TypeError) as e:
                raise ValueError('Confidence matrix incompatible with verified input chain order') from e
            forward,backward=finite_number(forward),finite_number(backward)
            if forward is None or backward is None:
                raise ValueError('Missing or nonfinite input-defined chain-pair confidence')
            values.append(forward)
            reverse.append(backward)
    for prefix,sequence in [('protein_to_ligand',values),('ligand_to_protein',reverse)]:
        features[prefix+'_iptm_mean']=sum(sequence)/len(sequence) if sequence else None
        features[prefix+'_iptm_min']=min(sequence) if sequence else None
        features[prefix+'_iptm_max']=max(sequence) if sequence else None
    return features
