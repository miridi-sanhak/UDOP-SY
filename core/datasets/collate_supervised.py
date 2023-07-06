import math
import collections
import pickle
import os
import random
import torch

import numpy as np
from transformers import PreTrainedTokenizerBase


class DataCollatorForSelfSupervisedTasks:

    def __init__(self, tokenizer=None, meta_path=None, input_length=None, target_length=None, pad_token_id=None, decoder_start_token_id=None):
        
        self.tokenizer = tokenizer
        self.input_length = input_length
        self.target_length = target_length
        self.pad_token_id = pad_token_id
        self.decoder_start_token_id = decoder_start_token_id

        self.LM = DataCollatorForT5LayoutModeling(
            tokenizer = self.tokenizer,
            input_length = self.input_length,
            target_length = self.target_length,
            pad_token_id = self.pad_token_id,
            decoder_start_token_id = self.decoder_start_token_id
        )

        self.VT = DataCollatorForT5VisTextRec(
            tokenizer = self.tokenizer,
            input_length = self.input_length,
            target_length = self.target_length,
            pad_token_id = self.pad_token_id,
            decoder_start_token_id = self.decoder_start_token_id
        )

        self.JR = DataCollatorForT5JointReconstruction(
            tokenizer = self.tokenizer,
            input_length = self.input_length,
            target_length = self.target_length,
            pad_token_id = self.pad_token_id,
            decoder_start_token_id = self.decoder_start_token_id
        )


    def __call__(self, task, ids_list, sentence_bbox, group_list, group_bbox_list, numbering_list):

        if task == 'Layout Modeling.':
            return self.LM(ids_list, sentence_bbox, group_list, group_bbox_list, numbering_list)
        
        elif task == 'Visual Text Recognition.':
            return self.VT(ids_list, sentence_bbox, group_list, group_bbox_list, numbering_list)
        
        elif task == 'Joint Text-Layout Reconstruction.':
            return self.JR(ids_list, sentence_bbox, group_list, group_bbox_list, numbering_list)
        
        else:
            raise ValueError("Invalid user prompt")


class DataCollatorForT5LayoutModeling:
    """
    Data collator used for T5 Layout Modeling
    """
    def __init__(self, tokenizer=None, meta_path=None, input_length=None, target_length=None, pad_token_id=None, decoder_start_token_id=None):

        self.tokenizer = tokenizer
        self.input_length = input_length
        self.target_length = target_length
        self.pad_token_id = pad_token_id
        self.decoder_start_token_id = decoder_start_token_id

    def __call__(self, input_ids, bbox_list, group_list, group_bbox_list, label_numbering):
        
        input_ids = []
        bbox_list = []

        labels = []
        for idx in range(len(label_numbering)):
            labels += self.tokenizer.encode(f'<extra_l_id_{label_numbering[idx]}>', add_special_tokens=False)
            labels += self.tokenizer.encode(f'<loc_{int(self.tokenizer._loc_extra_ids*group_bbox_list[idx][0])}>', add_special_tokens=False)
            labels += self.tokenizer.encode(f'<loc_{int(self.tokenizer._loc_extra_ids*group_bbox_list[idx][1])}>', add_special_tokens=False)
            labels += self.tokenizer.encode(f'<loc_{int(self.tokenizer._loc_extra_ids*group_bbox_list[idx][2])}>', add_special_tokens=False)
            labels += self.tokenizer.encode(f'<loc_{int(self.tokenizer._loc_extra_ids*group_bbox_list[idx][3])}>', add_special_tokens=False)
            
        slice_pointer=0
        L = len(group_list)
        input_len = len(input_ids)
        for i in range(input_len):
            if slice_pointer < L and i == group_list[slice_pointer][0]:
                input_ids += self.tokenizer.encode(f'<extra_l_id_{label_numbering[slice_pointer]}>', add_special_tokens=False)
                input_ids.append(input_ids[i])
                bbox_list.append([0,0,0,0])
                bbox_list.append(bbox_list[i])
            elif slice_pointer < L and i == group_list[slice_pointer][1] :
                input_ids += self.tokenizer.encode(f'</extra_l_id_{label_numbering[slice_pointer]}>', add_special_tokens=False)
                input_ids.append(input_ids[i])
                bbox_list.append([0,0,0,0])
                bbox_list.append(bbox_list[i])
                slice_pointer += 1
            else:
                input_ids.append(input_ids[i])
                bbox_list.append(bbox_list[i])
                
        if slice_pointer < L and input_len == group_list[slice_pointer][1] :
            input_ids += self.tokenizer.encode(f'</extra_l_id_{label_numbering[slice_pointer]}>', add_special_tokens=False)
            bbox_list.append([0,0,0,0])
        
        return input_ids, labels, bbox_list

class DataCollatorForT5VisTextRec:
    """
    Data collator used for T5 Visual Text Recognition
    """
    def __init__(self, tokenizer=None, meta_path=None, input_length=None, target_length=None, pad_token_id=None, decoder_start_token_id=None):

        self.tokenizer = tokenizer 
        self.input_length = input_length
        self.target_length = target_length
        self.pad_token_id = pad_token_id
        self.decoder_start_token_id = decoder_start_token_id

    def __call__(self, input_ids, bbox_list, group_list, group_bbox_list, label_numbering):

        input_ids = []
        bbox_list = []

        labels = []
        for idx in range(len(label_numbering)):
            labels += self.tokenizer.encode(f'<extra_t_id_{label_numbering[idx]}>', add_special_tokens=False)
            labels += input_ids[group_list[idx][0]:group_list[idx][1]]


        slice_pointer, idx = 0, 0
        L = len(group_list)
        len_ID = len(input_ids)

        while idx < len_ID:
            if slice_pointer < L and idx == group_list[slice_pointer][0]:
                input_ids += self.tokenizer.encode(f'<extra_t_id_{label_numbering[slice_pointer]}>', add_special_tokens=False)
                bbox_list.append([0,0,0,0])

                input_ids += self.tokenizer.encode(f'<loc_{int(self.tokenizer._loc_extra_ids*group_bbox_list[slice_pointer][0])}>', add_special_tokens=False)
                input_ids += self.tokenizer.encode(f'<loc_{int(self.tokenizer._loc_extra_ids*group_bbox_list[slice_pointer][1])}>', add_special_tokens=False)
                input_ids += self.tokenizer.encode(f'<loc_{int(self.tokenizer._loc_extra_ids*group_bbox_list[slice_pointer][2])}>', add_special_tokens=False)
                input_ids += self.tokenizer.encode(f'<loc_{int(self.tokenizer._loc_extra_ids*group_bbox_list[slice_pointer][3])}>', add_special_tokens=False)
                bbox_list += [[0,0,0,0]] * 4
                
                input_ids += self.tokenizer.encode(f'</extra_t_id_{label_numbering[slice_pointer]}>', add_special_tokens=False)
                bbox_list.append([0,0,0,0])
                idx = group_list[slice_pointer][1]-1
                slice_pointer += 1
            else:
                input_ids.append(input_ids[idx])
                bbox_list.append(bbox_list[idx])

            idx += 1

        return input_ids, labels, bbox_list


class DataCollatorForT5JointReconstruction:
    """
    Data collator used for T5 Joint Text-Layout Reconstruction
    """
    def __init__(self, tokenizer=None, meta_path=None, input_length=None, target_length=None, pad_token_id=None, decoder_start_token_id=None):

        self.tokenizer = tokenizer #이전에 만든 udop tokenizer를 불러옴
        self.input_length = input_length
        self.target_length = target_length
        self.pad_token_id = pad_token_id
        self.decoder_start_token_id = decoder_start_token_id

    def __call__(self, input_ids, bbox_list, group_list, group_bbox_list, label_numbering):
        
        input_ids = []
        bbox_list = []

        labels = []
        for idx in range(len(label_numbering)):
            labels += self.tokenizer.encode(f'<extra_id_{label_numbering[idx]}>', add_special_tokens=False)
            labels += input_ids[group_list[idx][0]:group_list[idx][1]]
            labels += self.tokenizer.encode(f'<loc_{int(self.tokenizer._loc_extra_ids * group_bbox_list[idx][0])}>', add_special_tokens=False)
            labels += self.tokenizer.encode(f'<loc_{int(self.tokenizer._loc_extra_ids * group_bbox_list[idx][1])}>', add_special_tokens=False)
            labels += self.tokenizer.encode(f'<loc_{int(self.tokenizer._loc_extra_ids * group_bbox_list[idx][2])}>', add_special_tokens=False)
            labels += self.tokenizer.encode(f'<loc_{int(self.tokenizer._loc_extra_ids * group_bbox_list[idx][3])}>', add_special_tokens=False)

        slice_pointer, idx = 0, 0
        L = len(group_list)
        len_ID = len(input_ids)
        
        while idx < len_ID:
            if slice_pointer < L and idx == group_list[slice_pointer][0]:
                input_ids += self.tokenizer.encode(f'<extra_id_{label_numbering[slice_pointer]}>', add_special_tokens=False)
                bbox_list.append([0,0,0,0])

                idx = group_list[slice_pointer][1]-1
                slice_pointer += 1
            else:
                input_ids.append(input_ids[idx])
                bbox_list.append(bbox_list[idx])
            
            idx += 1

        return input_ids, labels, bbox_list
    
