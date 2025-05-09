from PostProcessingBase import FlatNtupleBase

import os, re, sys, time, subprocess, math, json
import multiprocessing
from datetime import datetime
import hashlib

import ROOT

LorentzVector = ROOT.ROOT.Math.LorentzVector('ROOT::Math::PtEtaPhiM4D<double>')

class FlatNtupleForDstarFit(FlatNtupleBase):
    """Flat ROOT ntuple producer for BmmScout UML fit"""

    triggers_to_store = [
        # Run 3
        'HLT_ZeroBias',
        'HLT_DoubleMu4_3_LowMass',
    ]

    def _validate_inputs(self):
        """Task specific input validation"""

        # check for missing information
        for parameter in ['input', 'blind', 'cut', 'final_state', 'best_candidate']:
            if parameter not in self.job_info:
                raise Exception("Missing input '%s'" % parameter)

    def __select_candidates(self, candidates):
        """Select candidates to be stored"""
        
        if len(candidates) == 0 or self.job_info['best_candidate'] == "":
            return candidates

        # Find the best candidate
        best_candidate = None
        max_value = None
        values = getattr(self.event, self.job_info['best_candidate'])
        for i in candidates:
            if not best_candidate or max_value < values[i]:
                best_candidate = i
                max_value = values[i]

        return [best_candidate]
    
    def _process_events(self):
        """Event loop"""

        parsed_cut = self.get_cut()
                    
        for event_index, event in enumerate(self.input_tree):
            self.event = event           
            candidates = []

            # Trigger requirements
            if 'triggers' in self.job_info and len(self.job_info['triggers']) > 0:
                passed_trigger = False
                for trigger in  self.job_info['triggers']:
                    if hasattr(self.event, trigger):
                        if getattr(self.event, trigger):
                            passed_trigger = True
                            break
                if not passed_trigger:
                    continue
            
            # Find candidates the satisfy the selection requirements
            n = self.event.ndstar
            for cand in range(n):
                # if self.job_info['blind']:
                #     if self.job_info['final_state'] == 'mm':
                #         if self.event.mm_kin_mass[cand] < 5.50 and \
                #            self.event.mm_kin_mass[cand] > 5.15:
                #             continue
                #     if self.job_info['final_state'] == 'em':
                #         if self.event.mm_kin_mass[cand] < 5.70 and \
                #            self.event.mm_kin_mass[cand] > 5.10:
                #             continue
                
                # cut = self.job_info['cut'].format(cand=cand, tree="self.event")
                format_dict = { 'ndstar' : cand,
                                'tree' : 'self.event'}
                cut = parsed_cut.format(**format_dict)
                if not eval(cut):
                    continue

                candidates.append(cand)

            # Find canidates to be stored
            cands = self.__select_candidates(candidates)
            for cand in cands:
                self._fill_tree(cand, len(cands))
            

    def _configure_output_tree(self):
        ## event info
        self.tree.addBranch('run',         'UInt_t', 0, "Run number")
        self.tree.addBranch('ls',          'UInt_t', 0, "Luminosity section")
        self.tree.addBranch('evt',      'ULong64_t', 0, "Event number")
        self.tree.addBranch('npv',         'UInt_t', 0, "Number of good reconstructed primary vertices")
        self.tree.addBranch('npu',         'UInt_t', 0, "number of pileup interactions that have been added to the event in the current bunch crossing")
        self.tree.addBranch('npu_mean',   'Float_t', 0, "tru mean number of pileup interactions")
        self.tree.addBranch('certified_muon',    'Int_t', 0, "Event passed Muon Certification")
        self.tree.addBranch('certified_golden',  'Int_t', 0, "Event passed Golden Certification")
        self.tree.addBranch('n',           'UInt_t', 0, "Number of candidates")
        
        self.tree.addBranch('dm',         'Float_t', 0, "m(D*) - m(D0)")
        self.tree.addBranch('dm_kpi',     'Float_t', 0, "m(D*) - m(D0) D0->Kpi->mm")
        
        self.tree.addBranch('chan',        'UInt_t', 0, "0: Kpi, 1: pipi, 2: mumu")
        self.tree.addBranch('mc_match',     'Int_t', 0, "PdgId of MC matched Dstar")
        self.tree.addBranch('mc_signature', 'Int_t', 0, "Product of PdgIds of gen matched tracks")
        self.tree.addBranch('mc_d0_signature', 'Long64_t', 0, "Product of PDG ids of gen decay products of MC matched D0")
        self.tree.addBranch('mc_parent',    'Int_t', 0, "PdgId of MC matched parent of Dstar")
        self.tree.addBranch('mc_d0_ancestor', 'Int_t', 0, "PdgId of a common ancestor of D0 decay products")
        self.tree.addBranch('mc_dstar_ancestor', 'Int_t', 0, "PdgId of a common ancestor of Dstar decay products")

        self.tree.addBranch('dstar_vtx_prob', 'Float_t', 0, "D* PV with soft pion probability")
        # self.tree.addBranch('dstar_pt',       'Float_t', 0, "D* pt")
        # self.tree.addBranch('dstar_m',        'Float_t', 0, "D* mass")
        # self.tree.addBranch('dstar_me',       'Float_t', 0, "D* mass error")
        self.tree.addBranch('dstar_pi_pt',    'Float_t', 0, "Soft pion pt")
        self.tree.addBranch('dstar_pi_eta',   'Float_t', 0, "Soft pion eta")
        self.tree.addBranch('dstar_pi_phi',   'Float_t', 0, "Soft pion phi")

        self.tree.addBranch('d0_vtx_prob', 'Float_t', 0, "D0 vtx probability")
        self.tree.addBranch('d0_pt',       'Float_t', 0, "D0 pt")
        self.tree.addBranch('d0_eta',      'Float_t', 0, "D0 eta")
        self.tree.addBranch('d0_phi',      'Float_t', 0, "D0 phi")
        self.tree.addBranch('d0_m',        'Float_t', 0, "D0 mass")
        self.tree.addBranch('d0_kpi_m',    'Float_t', 0, "D0->Kpi->mm mass")
        self.tree.addBranch('d0_me',       'Float_t', 0, "D0 mass error")
        self.tree.addBranch('d0_d1_pt',    'Float_t', 0, "D0 daughter1 pt")
        self.tree.addBranch('d0_d1_eta',   'Float_t', 0, "D0 daughter1 eta")
        self.tree.addBranch('d0_d1_phi',   'Float_t', 0, "D0 daughter1 phi")
        self.tree.addBranch('d0_d2_pt',    'Float_t', 0, "D0 daughter2 pt")
        self.tree.addBranch('d0_d2_eta',   'Float_t', 0, "D0 daughter2 eta")
        self.tree.addBranch('d0_d2_phi',   'Float_t', 0, "D0 daughter2 phi")
        self.tree.addBranch('d0_pvip',     'Float_t', 0, "D0 impact parameter wrt Primary Vertex in 3D")
        self.tree.addBranch('d0_spvip',    'Float_t', 0, "D0 impact parameter significance wrt Primary Vertex in 3D")

        self.tree.addBranch('d0_alpha',    'Float_t', 0, "D0 pointing angle")
        self.tree.addBranch('d0_alphaBS',  'Float_t', 0, "D0 pointing angle 2D wrt BS")
        self.tree.addBranch('d0_sl3d',     'Float_t', 0, "D0 significance of flight length 3D")
        self.tree.addBranch('d0_d1_muid',  'Float_t', -1, "D0 daughter1 soft mva muon id")
        self.tree.addBranch('d0_d2_muid',  'Float_t', -1, "D0 daughter2 soft mva muon id")
        
        for trigger in self.triggers_to_store:
            self.tree.addBranch(trigger, 'Int_t', -1, "Trigger decision: 1 - fired, 0 - didn't fire, -1 - no information")
            # self.tree.addBranch("%s_ps" % trigger, 'UInt_t', 999999, "Prescale. 0 - Off, 999999 - no information")
            self.tree.addBranch("%s_ps" % trigger, 'Float_t', 999999, "Prescale. 0 - Off, 999999 - no information")
            # self.tree.addBranch("%s_matched" % trigger, 'Int_t', 0,  "matched to the trigger objets")

    def _fill_tree(self, cand, ncands):
        self.tree.reset()

        ## event info
        self.tree['run'] = self.event.run
        self.tree['ls']  = self.event.luminosityBlock
        self.tree['evt'] = self.event.event
        self.tree['npv'] = ord(self.event.PV_npvsGood) if isinstance(self.event.PV_npvsGood, str) else self.event.PV_npvsGood

        ## fill MC information
        if hasattr(self.event, 'Pileup_nTrueInt'):
            self.tree['npu']      = self.event.Pileup_nPU
            self.tree['npu_mean'] = self.event.Pileup_nTrueInt
            self.tree['mc_match'] = self.event.dstar_gen_pdgId[cand]
            self.tree['mc_signature'] = self.event.dstar_gen_pion_pdgId[cand]
            self.tree['mc_parent'] = self.event.dstar_gen_mpdgId[cand]
            self.tree['mc_dstar_ancestor'] = self.event.dstar_gen_cpdgId[cand]

        self.tree['certified_muon']   = self._is_certified(self.event, "muon")
        self.tree['certified_golden'] = self._is_certified(self.event, "golden")
        self.tree['n']   = ncands

        if self.job_info['final_state'] in ['dzpipi', 'dzkpi']:
            # pipi final state
            if self.event.dstar_hh_index[cand] >= 0:
                hh_index = self.event.dstar_hh_index[cand]
                signature = self.event.hh_had1_pdgId[hh_index] * self.event.hh_had2_pdgId[hh_index]
                if (self.job_info['final_state'] == 'dzpipi' and signature == -211 * 211) or \
                   (self.job_info['final_state'] == 'dzkpi' and signature == -321 * 211) :

                    if self.job_info['final_state'] == 'dzkpi':
                        self.tree['chan'] = 0
                    if self.job_info['final_state'] == 'dzpipi':
                        self.tree['chan'] = 1

                    if hasattr(self.event, 'Pileup_nTrueInt') and hasattr(self.event, 'nGenPart'):
                        self.tree['mc_signature'] *= self.event.hh_gen_had1_pdgId[hh_index]
                        self.tree['mc_signature'] *= self.event.hh_gen_had2_pdgId[hh_index]
                        if self.event.hh_gen_cindex[hh_index] >= 0:
                            self.tree['mc_d0_signature'] = 1
                            for igen in range(self.event.nGenPart):
                                if self.event.GenPart_genPartIdxMother[igen] == self.event.hh_gen_cindex[hh_index]:
                                    self.tree['mc_d0_signature'] *= self.event.GenPart_pdgId[igen]
                        else:
                            self.tree['mc_d0_signature'] = 0

                    self.tree['dm'] = self.event.dstar_dm_pv[cand]

                    self.tree['dstar_vtx_prob'] = self.event.dstar_pv_with_pion_prob[cand]
                    self.tree['dstar_pi_pt']    = self.event.dstar_pion_pt[cand]
                    self.tree['dstar_pi_eta']   = self.event.dstar_pion_eta[cand]
                    self.tree['dstar_pi_phi']   = self.event.dstar_pion_phi[cand]

                    self.tree['d0_vtx_prob']    = self.event.hh_kin_vtx_prob[hh_index]
                    self.tree['d0_pt']          = self.event.hh_kin_pt[hh_index]
                    self.tree['d0_eta']         = self.event.hh_kin_eta[hh_index]
                    self.tree['d0_phi']         = self.event.hh_kin_phi[hh_index]
                    self.tree['d0_m']           = self.event.hh_kin_mass[hh_index]
                    self.tree['d0_me']          = self.event.hh_kin_massErr[hh_index]
                    if self.event.hh_kin_had1_pt[hh_index] >= self.event.hh_kin_had2_pt[hh_index]: 
                        self.tree['d0_d1_pt']       = self.event.hh_kin_had1_pt[hh_index]
                        self.tree['d0_d1_eta']      = self.event.hh_kin_had1_eta[hh_index]
                        self.tree['d0_d1_phi']      = self.event.hh_kin_had1_phi[hh_index]
                        self.tree['d0_d2_pt']       = self.event.hh_kin_had2_pt[hh_index]
                        self.tree['d0_d2_eta']      = self.event.hh_kin_had2_eta[hh_index]
                        self.tree['d0_d2_phi']      = self.event.hh_kin_had2_phi[hh_index]
                    else:
                        self.tree['d0_d2_pt']       = self.event.hh_kin_had1_pt[hh_index]
                        self.tree['d0_d2_eta']      = self.event.hh_kin_had1_eta[hh_index]
                        self.tree['d0_d2_phi']      = self.event.hh_kin_had1_phi[hh_index]
                        self.tree['d0_d1_pt']       = self.event.hh_kin_had2_pt[hh_index]
                        self.tree['d0_d1_eta']      = self.event.hh_kin_had2_eta[hh_index]
                        self.tree['d0_d1_phi']      = self.event.hh_kin_had2_phi[hh_index]
                    self.tree['d0_spvip']       = self.event.hh_kin_spvip[hh_index]
                    self.tree['d0_pvip']        = self.event.hh_kin_pvip[hh_index]

                    self.tree['d0_alpha']       = self.event.hh_kin_alpha[hh_index]
                    self.tree['d0_alphaBS']     = self.event.hh_kin_alphaBS[hh_index]
                    self.tree['d0_sl3d']        = self.event.hh_kin_sl3d[hh_index]
                    
                    if hasattr(self.event, 'hh_gen_cpdgId'):
                        self.tree['mc_d0_ancestor'] = self.event.hh_gen_cpdgId[hh_index]

        elif self.job_info['final_state'] == 'dzmm':
            # mm final state
            if self.event.dstar_mm_index[cand] >= 0:
                
                self.tree['chan'] = 2
                mm_index = self.event.dstar_mm_index[cand]

                if hasattr(self.event, 'Pileup_nTrueInt'):
                    self.tree['mc_signature'] *= self.event.mm_gen_mu1_pdgId[mm_index]
                    self.tree['mc_signature'] *= self.event.mm_gen_mu2_pdgId[mm_index]
                    if self.event.mm_gen_cindex[mm_index] >= 0:
                        self.tree['mc_d0_signature'] = 1
                        for igen in range(self.event.nGenPart):
                            if self.event.GenPart_genPartIdxMother[igen] == self.event.mm_gen_cindex[mm_index]:
                                self.tree['mc_d0_signature'] *= self.event.GenPart_pdgId[igen]
                    else:
                        self.tree['mc_d0_signature'] = 0

                self.tree['dm'] = self.event.dstar_dm_pv[cand]

                self.tree['dstar_vtx_prob'] = self.event.dstar_pv_with_pion_prob[cand]
                self.tree['dstar_pi_pt']    = self.event.dstar_pion_pt[cand]
                self.tree['dstar_pi_eta']   = self.event.dstar_pion_eta[cand]
                self.tree['dstar_pi_phi']   = self.event.dstar_pion_phi[cand]

                self.tree['d0_vtx_prob']    = self.event.mm_kin_vtx_prob[mm_index]
                self.tree['d0_pt']          = self.event.mm_kin_pt[mm_index]
                self.tree['d0_eta']         = self.event.mm_kin_eta[mm_index]
                self.tree['d0_phi']         = self.event.mm_kin_phi[mm_index]
                self.tree['d0_m']           = self.event.mm_kin_mass[mm_index]
                self.tree['d0_me']          = self.event.mm_kin_massErr[mm_index]
                if self.event.mm_kin_mu1_pt[mm_index] >= self.event.mm_kin_mu2_pt[mm_index]: 
                    self.tree['d0_d1_pt']       = self.event.mm_kin_mu1_pt[mm_index]
                    self.tree['d0_d1_eta']      = self.event.mm_kin_mu1_eta[mm_index]
                    self.tree['d0_d1_phi']      = self.event.mm_kin_mu1_phi[mm_index]
                    self.tree['d0_d2_pt']       = self.event.mm_kin_mu2_pt[mm_index]
                    self.tree['d0_d2_eta']      = self.event.mm_kin_mu2_eta[mm_index]
                    self.tree['d0_d2_phi']      = self.event.mm_kin_mu2_phi[mm_index]
                else:
                    self.tree['d0_d2_pt']       = self.event.mm_kin_mu1_pt[mm_index]
                    self.tree['d0_d2_eta']      = self.event.mm_kin_mu1_eta[mm_index]
                    self.tree['d0_d2_phi']      = self.event.mm_kin_mu1_phi[mm_index]
                    self.tree['d0_d1_pt']       = self.event.mm_kin_mu2_pt[mm_index]
                    self.tree['d0_d1_eta']      = self.event.mm_kin_mu2_eta[mm_index]
                    self.tree['d0_d1_phi']      = self.event.mm_kin_mu2_phi[mm_index]
                self.tree['d0_spvip']       = self.event.mm_kin_spvip[mm_index]
                self.tree['d0_pvip']        = self.event.mm_kin_pvip[mm_index]
                self.tree['d0_d1_muid']     = self.event.Muon_softMva[self.event.mm_mu1_index[mm_index]]
                self.tree['d0_d2_muid']     = self.event.Muon_softMva[self.event.mm_mu2_index[mm_index]]

                self.tree['d0_alpha']       = self.event.mm_kin_alpha[mm_index]
                self.tree['d0_alphaBS']     = self.event.mm_kin_alphaBS[mm_index]
                self.tree['d0_sl3d']        = self.event.mm_kin_sl3d[mm_index]

                # D0->Kpi->mm
                # kaon charge is negative
                # muon PDG id signa is opposite of its charge
                if self.event.dstar_pion_charge[cand] * self.event.mm_mu1_pdgId[mm_index] > 0:
                    kaon_mu_index = self.event.mm_mu1_index[mm_index]
                    pion_mu_index = self.event.mm_mu2_index[mm_index]
                else:
                    kaon_mu_index = self.event.mm_mu2_index[mm_index]
                    pion_mu_index = self.event.mm_mu1_index[mm_index]

                kaon_p4 = LorentzVector(self.event.Muon_pt[kaon_mu_index],
                                        self.event.Muon_eta[kaon_mu_index],
                                        self.event.Muon_phi[kaon_mu_index], 0.497648)
                    
                pion_p4 = LorentzVector(self.event.Muon_pt[pion_mu_index],
                                        self.event.Muon_eta[pion_mu_index],
                                        self.event.Muon_phi[pion_mu_index], 0.139570)
                    
                soft_p4 = LorentzVector(self.event.dstar_pion_pt[cand],
                                        self.event.dstar_pion_eta[cand],
                                        self.event.dstar_pion_phi[cand], 0.139570)
                
                self.tree['d0_kpi_m'] = (kaon_p4 + pion_p4).mass()
                
                self.tree['dm_kpi'] = (kaon_p4 + pion_p4 + soft_p4).mass() - self.tree['d0_kpi_m']
                
                if hasattr(self.event, 'mm_gen_cpdgId'):
                    self.tree['mc_d0_ancestor'] = self.event.mm_gen_cpdgId[mm_index]
        else:
            raise Exception("Unsupported final state: %s" % self.job_info['final_state'])

        for trigger in self.triggers_to_store:
            if hasattr(self.event, trigger):
                self.tree[trigger] = getattr(self.event, trigger)
            if hasattr(self.event, "prescale_" + trigger):
                self.tree[trigger + "_ps"] = getattr(self.event, "prescale_" + trigger)
        
        self.tree.fill()

if __name__ == "__main__":

    ### create a test job
    
    common_branches = 'PV_npvs|PV_npvsGood|Pileup_nTrueInt|Pileup_nPU|run|event|luminosityBlock'
    
    # job = {
    #     "input": [
    #         # "root://eoscms.cern.ch://eos/cms/store/group/phys_bphys/bmm/bmm6/NanoAOD/523/DstarToD0Pi_D0To2Mu_SoftQCDnonD_TuneCP5_13p6TeV_pythia8-evtgen+Run3Summer22MiniAODv3-124X_mcRun3_2022_realistic_v12-v2+MINIAODSIM/089fcee0-0260-470b-8f08-a458129f2c4a.root"
    #     ],
    #     "signal_only" : False,
    #     "tree_name" : "dzmmMC",
    #     "blind" : False,
    #     "triggers":['HLT_DoubleMu4_3_LowMass'],
    #     "cut" :
    #         "dstar_mm_index>=0 and Muon_softMva[mm_mu1_index[dstar_mm_index]] > 0.45 and "\
    #         "Muon_softMva[mm_mu2_index[dstar_mm_index]] > 0.45 and "\
    #         "mm_mu1_pt[dstar_mm_index]>4 and mm_mu2_pt[dstar_mm_index]>4 and "\
    #         "mm_kin_alpha[dstar_mm_index]<0.1 and mm_kin_sl3d[dstar_mm_index]>3 and "\
    #         "mm_kin_vtx_prob[dstar_mm_index]>0.01 and dstar_pv_with_pion_prob>0.1 and "\
    #         "dstar_dm_pv>0.140 and dstar_dm_pv<0.155 and "\
    #         "mm_kin_mass[dstar_mm_index]>1.81 and mm_kin_mass[dstar_mm_index]<1.94",
    #     "final_state" : "dstar",
    #     "best_candidate": "",
    #   }

    # job = {
    #     "input": [
    #         'root://eoscms.cern.ch://eos/cms/store/group/phys_muon/dmytro/tmp/DstarToD0Pi_D0To2Pi_SoftQCDnonD_TuneCP5_13p6TeV_pythia8-evtgen.root'
    #     ],
    #     "signal_only" : False,
    #     "tree_name" : "dzpipiMC",
    #     "blind" : False,
    #     "triggers":[],
    #     "cut" : (
    #         "dstar_hh_index>=0 and "
    #         "hh_had1_pt[dstar_hh_index]>4 and hh_had2_pt[dstar_hh_index]>4 and "
    #         "hh_kin_alpha[dstar_hh_index]<0.1 and hh_kin_sl3d[dstar_hh_index]>3 and "
    #         "hh_kin_vtx_prob[dstar_hh_index]>0.01 and dstar_pv_with_pion_prob>0.1 and "
    #         "dstar_dm_pv>0.140 and dstar_dm_pv<0.155 and "
    #         "hh_kin_mass[dstar_hh_index]>1.81 and hh_kin_mass[dstar_hh_index]<1.94 and "
    #         "hh_had1_pdgId[dstar_hh_index] * hh_had2_pdgId[dstar_hh_index] == - 211 * 211"
    #     ),
    #     "final_state" : "dzpipi",
    #     "best_candidate": "",
    #   }

    input_path = "/eos/cms/store/group/phys_bphys/bmm/bmm6/PostProcessing/Skims/529/dzkpimm/InclusiveDileptonMinBias_TuneCP5Plus_13p6TeV_pythia8+Run3Summer22MiniAODv3-Pilot_124X_mcRun3_2022_realistic_v12-v5+MINIAODSIM/"
    job = {
        "input": [
            input_path + "016efedcfb512dc565f3c12ed733bd36.root",
            input_path + "5b902bfcd14e27228d9e3ef0e62f77ac.root",
            input_path + "198b4ac8be5b86428a0060af0b2c9fb0.root",
            input_path + "4adaa92b58ed22c509c0d78d43863a6f.root",
            input_path + "8b66894bb677aa556e83ea30f305eaa9.root",
            input_path + "b24b04b46c6efebc23a82c9feea852fa.root",
            input_path + "6d90f1337f551d51cb070f63ecd76a0c.root",
            input_path + "47bd4fb54daef9c5e281e98e5007081a.root",
            input_path + "43db4b25b39dc2698ea307269c3cfcd8.root",
            input_path + "2d09fe05fc08d23696fa471d54157ff3.root",
            input_path + "5694d5997d63bd72f8cbce8803c85235.root",
            input_path + "71f1534316bfd0635d4344417cea5953.root",
            input_path + "06b35e7ff81bf7944b55bfa132a413ed.root",
            input_path + "b1776360b268e61474b929878641293e.root",
            input_path + "1bbc2b0ff8ecdeb2a9dd519bb95c3cba.root",
            input_path + "6699e4a7763ee81656d85c4f812b789d.root",
            input_path + "25aedb32644787efc5c23d6fb757e0bc.root",
            input_path + "4bb41e7ec4baa739c16f407fa6406b02.root",
            input_path + "0faa06bc41097fc29457284027af3c99.root",
            input_path + "41c4a6f9b52125bdf0668d40734b36ee.root",
            # '/eos/cms/store/group/phys_bphys/bmm/bmm6/NanoAOD/529/InclusiveDileptonMinBias_TuneCP5Plus_13p6TeV_pythia8+Run3Summer22MiniAODv3-Pilot_124X_mcRun3_2022_realistic_v12-v5+MINIAODSIM/6516d29c-8ef7-4142-a9ff-da9ba5b3f787.root',
        ],
        "signal_only" : False,
        "tree_name" : "dzmmMC",
        "blind" : False,
        "triggers":[],
        "cut" : (
            "dstar_mm_index>=0 and "
            # "mm_mu1_pt[dstar_mm_index]>4 and mm_mu2_pt[dstar_mm_index]>4 and "
            # "mm_kin_alpha[dstar_mm_index]<0.1 and mm_kin_sl3d[dstar_mm_index]>3 and "
            # "mm_kin_vtx_prob[dstar_mm_index]>0.01 and dstar_pv_with_pion_prob>0.1 and "
            "dstar_dm_pv>0.140 and dstar_dm_pv<0.155 and "
            "mm_kin_mass[dstar_mm_index]>1.5 and mm_kin_mass[dstar_mm_index]<1.94"
        ),
        "final_state" : "dzmm",
        "best_candidate": "",
      }

    # job = {
    #     "input": [
    #         'root://eoscms.cern.ch://eos/cms/store/group/phys_bphys/bmm/bmm6/NanoAOD/526/ParkingDoubleMuonLowMass5+Run2022C-PromptReco-v1+MINIAOD/3237cbb0-122b-4d28-bebf-dea5da307147.root',
    #     ],
    #     "signal_only" : False,
    #     "tree_name" : "dzmmData",
    #     "blind" : False,
    #     "triggers":["HLT_DoubleMu4_3_LowMass"],
    #     "pre-selection":"dstar_mm_index>=0 && dstar_dm_pv>0.140 && dstar_dm_pv<0.155",
    #     "pre-selection-keep":"^(dstar_.*|ndstar|mm_.*|nmm|Muon_.*|nMuon|HLT_DoubleMu4_3_LowMass|" + common_branches + ")$",
    #     "cut" : (
    #         "dstar_mm_index>=0 and "
    #         "mm_mu1_pt[dstar_mm_index]>4 and mm_mu2_pt[dstar_mm_index]>4 and "
    #         "mm_kin_alpha[dstar_mm_index]<0.1 and mm_kin_sl3d[dstar_mm_index]>3 and "
    #         "mm_kin_vtx_prob[dstar_mm_index]>0.01 and dstar_pv_with_pion_prob>0.1 and "
    #         "dstar_dm_pv>0.140 and dstar_dm_pv<0.155 and "
    #         "mm_kin_mass[dstar_mm_index]>1.81 and mm_kin_mass[dstar_mm_index]<1.94"
    #     ),
    #     "final_state" : "dzmm",
    #     "best_candidate": "",
    #   }
    
    file_name = "/tmp/dmytro/test.job"
    json.dump(job, open(file_name, "w"))
    
    # p = FlatNtupleForDstarFit("/eos/cms/store/group/phys_bphys/bmm/bmm6/PostProcessing/FlatNtuples/526/dzkpi/ZeroBias+Run2022F-PromptReco-v1+MINIAOD/00fa2c63d9f5bbb1ab34a51281bdb2d7.job")
    p = FlatNtupleForDstarFit(file_name)

    print(p.__dict__)
        
    p.process()
