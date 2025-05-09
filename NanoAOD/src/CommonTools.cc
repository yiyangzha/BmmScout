#include "BmmScout/NanoAOD/interface/CommonTools.h"
#include "DataFormats/Math/interface/deltaR.h"

using namespace bmm;

unsigned int
CloseTrackInfo::nTracksByVertexProbability(double minProb, 
					   double minIpSignificance,
					   int pvIndex,
					   const pat::PackedCandidate* ignoreTrack1)
{
  unsigned int n = 0;
  for (auto track: tracks){
    if (ignoreTrack1 and track.pfCand==ignoreTrack1) continue;
    if (minIpSignificance>0 and track.impactParameterSignificanceBS<minIpSignificance) continue;
    if (track.svProb<minProb) continue;
    if (pvIndex >= 0 and int(track.pfCand->vertexRef().key())!=pvIndex) continue;
    n++;
  }
  return n;
}

unsigned int
CloseTrackInfo::nTracksByDisplacementSignificance(double max_svDoca, 
						  double maxSignificance,
						  int pvIndex,
						  const pat::PackedCandidate* ignoreTrack1)
{
  unsigned int n = 0;
  for (auto track: tracks){
    if (track.svDoca>max_svDoca) continue;
    if (ignoreTrack1 and track.pfCand==ignoreTrack1) continue;
    if (maxSignificance>0 and (track.svDocaErr<=0 or 
			       track.svDoca/track.svDocaErr > maxSignificance) ) continue;
    if (pvIndex >= 0 and int(track.pfCand->vertexRef().key())!=pvIndex) continue;
    n++;
  }
  return n;
}

unsigned int
CloseTrackInfo::nTracksByBetterMatch(double max_svDoca, 
				     double maxSignificance,
				     int pvIndex,
				     const pat::PackedCandidate* ignoreTrack1)
{
  unsigned int n = 0;
  for (auto track: tracks){
    if (track.svDoca>max_svDoca) continue;
    if (ignoreTrack1 and track.pfCand==ignoreTrack1) continue;
    if (maxSignificance>0 and (track.svDocaErr<=0 or 
			       track.svDoca/track.svDocaErr > maxSignificance) ) continue;
    if (track.svDocaErr<=0 or (track.pvDocaErr>0 and track.svDoca/track.svDocaErr > track.pvDoca/track.pvDocaErr) ) continue;
    if (pvIndex >= 0 and int(track.pfCand->vertexRef().key())!=pvIndex) continue;
    n++;
  }
  return n;
}

float
CloseTrackInfo::minDoca(double max_svDoca, 
			int pvIndex,
			const pat::PackedCandidate* ignoreTrack1)
{
  float doca = 99.;
  for (auto track: tracks){
    if (track.svDoca>max_svDoca) continue;
    if (ignoreTrack1 and track.pfCand==ignoreTrack1) continue;
    if (pvIndex >= 0 and int(track.pfCand->vertexRef().key())!=pvIndex) continue;
    if (doca>track.svDoca) doca = track.svDoca;
  }
  return doca;
}
    
void
CloseTrackInfo::fillCandInfo(pat::CompositeCandidate& cand, int pvIndex, std::string name)
{
  if (name!="") name += "_";
  cand.addUserInt(   name + "nTrks",       nTracksByVertexProbability(0.1,-1.0,pvIndex) );
  cand.addUserInt(   name + "nBMTrks",     nTracksByBetterMatch() );
  cand.addUserInt(   name + "nDisTrks",    nTracksByVertexProbability(0.1, 2.0,pvIndex) );
  cand.addUserInt(   name + "closetrk",    nTracksByDisplacementSignificance(0.03, -1, pvIndex) );
  cand.addUserInt(   name + "closetrks1",  nTracksByDisplacementSignificance(0.03, 1, pvIndex) );
  cand.addUserInt(   name + "closetrks2",  nTracksByDisplacementSignificance(0.03, 2, pvIndex) );
  cand.addUserInt(   name + "closetrks3",  nTracksByDisplacementSignificance(0.03, 3, pvIndex) );
  cand.addUserFloat( name + "docatrk",     minDoca(0.03, pvIndex) );
}

std::vector<unsigned int> 
bmm::get_depth_from_permutation(const std::vector<unsigned int>& elements){
  std::vector<unsigned int> result;
  unsigned int counter(0);
  for (auto element: elements){
    if (element==0){
      counter++;
    } else {
      result.push_back(counter);
      counter = 0;
    }
  }
  result.push_back(counter);
  return result;
}

bool
bmm::is_acceptable(const reco::Candidate* cand){
  if ( not cand) return false; 
  // skip quarks
  if ( abs(cand->pdgId())<10 ) return false;
  // skip protons
  if ( abs(cand->pdgId())==2212 ) return false;
  // skip gluons
  if ( abs(cand->pdgId())==21 ) return false;
  return true;
}

const reco::Candidate*
bmm::get_mother(const reco::Candidate* cand, unsigned int depth){
  if (not cand) return 0;
  const reco::Candidate* mother = cand->mother();
  unsigned int i = 0;
  while ( is_acceptable(mother) and i<depth ){
    i++;
    mother = mother->mother();
  }
  if (is_acceptable(mother))
    return mother;
  else
    return 0;
}

const reco::Candidate* 
bmm::find_common_ancestor(const std::vector<const reco::Candidate*>& particles, 
		     unsigned int max_depth){
  auto n = particles.size();
  for (unsigned int depth=0; depth<max_depth; ++depth){
    // make a list of elements (0) and separators (1) and
    // find all possible permutations of the elements
    std::vector<unsigned int> elements;
    for (unsigned int i=0; i<depth; ++i)
      elements.push_back(0);
    for (unsigned int i=0; i<n-1; ++i)
      elements.push_back(1);
    do {
      auto depth_vector = get_depth_from_permutation(elements);
      const reco::Candidate* common_mother(0);
      for (unsigned int i=0; i<n; ++i){
	auto mother = get_mother(particles[i],depth_vector[i]);
	if (not mother) {
	  common_mother = 0;
	  break;
	}
	if (not common_mother) common_mother = mother;
	if (common_mother != mother) {
	  common_mother = 0;
	  break;
	}	  
      }
      if (common_mother) return common_mother;
    } while(std::next_permutation(elements.begin(), elements.end()));
  }
  return 0;
}

int bmm::get_pixel_pattern(const reco::HitPattern& hit_pattern) {
  // using int is safe since we don't expect more than 8 bits
  int pattern(0);
  for (unsigned int layer=1; layer <= 4; ++layer) {
    if (hit_pattern.hasValidHitInPixelLayer(PixelSubdetector::PixelBarrel, layer))
      pattern += 1 << (layer - 1);
  }
  for (unsigned int disk=1; disk <= 3; ++disk) {
    if (hit_pattern.hasValidHitInPixelLayer(PixelSubdetector::PixelEndcap, disk))
      pattern += 1 << (disk + 3);
  }
  return pattern;
}

void bmm::fill_track_info(pat::CompositeCandidate& cand, const reco::Track* track, std::string prefix)
{
  if (track) {
    cand.addUserFloat(prefix + "trkValidFrac",  track->validFraction());
    cand.addUserFloat(prefix + "trkNormChi2",   track->normalizedChi2());
	
    cand.addUserInt(prefix + "pixelPattern",    bmm::get_pixel_pattern(track->hitPattern()));
    cand.addUserInt(prefix + "nPixels",         track->hitPattern().numberOfValidPixelHits());
    cand.addUserInt(prefix + "nValidHits",      track->hitPattern().numberOfValidTrackerHits());
    cand.addUserInt(prefix + "nLostHitsInner",  track->hitPattern().numberOfLostTrackerHits(reco::HitPattern::MISSING_INNER_HITS));
    cand.addUserInt(prefix + "nLostHitsOn",     track->hitPattern().numberOfLostTrackerHits(reco::HitPattern::TRACK_HITS));
    cand.addUserInt(prefix + "nLostHitsOuter",  track->hitPattern().numberOfLostTrackerHits(reco::HitPattern::MISSING_OUTER_HITS));
	
    cand.addUserInt(prefix + "trkLayers",           track->hitPattern().trackerLayersWithMeasurement());
    cand.addUserInt(prefix + "trkLostLayersInner",  track->hitPattern().trackerLayersWithoutMeasurement(reco::HitPattern::MISSING_INNER_HITS));
    cand.addUserInt(prefix + "trkLostLayersOn",     track->hitPattern().trackerLayersWithoutMeasurement(reco::HitPattern::TRACK_HITS));
    cand.addUserInt(prefix + "trkLostLayersOuter",  track->hitPattern().trackerLayersWithoutMeasurement(reco::HitPattern::MISSING_OUTER_HITS));

    cand.addUserInt(prefix + "highPurity",   track->quality(reco::Track::highPurity));

  } else {
    cand.addUserFloat(prefix + "trkValidFrac",  0);
    cand.addUserFloat(prefix + "trkNormChi2",   9999.);
    
    cand.addUserInt(prefix + "pixelPattern",    0);
    cand.addUserInt(prefix + "nPixels",         0);
    cand.addUserInt(prefix + "nValidHits",      0);
    cand.addUserInt(prefix + "nLostHitsInner",  0);
    cand.addUserInt(prefix + "nLostHitsOn",     0);
    cand.addUserInt(prefix + "nLostHitsOuter",  0);
    
    cand.addUserInt(prefix + "trkLayers",           0);
    cand.addUserInt(prefix + "trkLostLayersInner",  0);
    cand.addUserInt(prefix + "trkLostLayersOn",     0);
    cand.addUserInt(prefix + "trkLostLayersOuter",  0);
    
    cand.addUserInt(prefix + "highPurity",   0);
  }

}

