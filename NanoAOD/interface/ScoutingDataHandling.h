#ifndef BmmScout_NanoAOD_ScoutingDataHandling_h
#define BmmScout_NanoAOD_ScoutingDataHandling_h

#include "DataFormats/TrackReco/interface/Track.h"
#include "DataFormats/VertexReco/interface/Vertex.h"
#include "DataFormats/Scouting/interface/Run3ScoutingTrack.h"
#include "DataFormats/PatCandidates/interface/Muon.h"
#include "DataFormats/Scouting/interface/Run3ScoutingMuon.h"
#include "DataFormats/Scouting/interface/Run3ScoutingVertex.h"

namespace bmm {
  typedef reco::Candidate::LorentzVector LorentzVector;
  typedef reco::Candidate::PolarLorentzVector PolarLorentzVector;
  
  // Tracks
  reco::Track makeRecoTrack(const Run3ScoutingTrack&);
  reco::Track makeRecoTrack(const Run3ScoutingMuon&);
  Run3ScoutingTrack makeScoutingTrack(const reco::Track&);
  PolarLorentzVector makePolarLorentzVector(const Run3ScoutingTrack&, float mass);

  // Muons
  pat::Muon makePatMuon(const Run3ScoutingMuon&);

  // Vertex
  reco::Vertex makeRecoVertex(const Run3ScoutingVertex&);
}

#endif
