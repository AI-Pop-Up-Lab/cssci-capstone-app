/*
Page that shows the results of the synthetic panels
Countries can be picked to see that country's data
Graphs shown:
- bar chart of vote distribution across parties
- a map of the country and the most popular party in each region
- a seat projection chart
- a bar chart that can be filtered by demographics, to show vote distribution across various demographics

Sample and frame data used for charts seen also downloadable here
*/

import { useState, useEffect } from "react";
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';

import './pollPage.css';

import CountrySwitch2 from '../modules/countrySwitch2';

import PollingMap from '../modules/polling_results_modules/pollingMap';
import SeatVisualisation from '../modules/polling_results_modules/seatVisualisation';
import VoteProjection from '../modules/polling_results_modules/voteProjection';
import DemographicCharts from '../modules/polling_results_modules/demographicCharts';
import VoteLongitudinal from "../modules/polling_results_modules/voteLongitudinal";
import VoteLongitudinalDemographics from "../modules/polling_results_modules/voteLongitudinalDemographics";
import PollstersUS from "../modules/polling_results_modules/pollstersUS";
import VoteLongitudinalUSPollsters from "../modules/polling_results_modules/voteLongitudinalUSPollsters";

import { getCountryData } from '../utils/fetch_data';
import { getChosenCountry, setChosenCountry } from '../utils/set_country';
import { COUNTRY_INFO } from '../utils/common_vars'

function PollPage() {

  const [selectedCountry, setSelectedCountry] = useState(() => getChosenCountry() ?? "usa");

  const [countryData, setCountryData] = useState(null);

  useEffect(() => {
    let cancelled = false;

    getCountryData(selectedCountry)
      .then((data) => {
        if (!cancelled) setCountryData(data);
      })
      .catch((err) => {
        console.error('Failed to load country data:', err);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedCountry]);

  function handleCountryChange(country) {
    setChosenCountry(country);
    setSelectedCountry(country);
  }

  return (
    <div className="PollPage unbounded-weight300">
      {/* Component for switching country */}
      <CountrySwitch2 
        setCountry={handleCountryChange} 
        selectedCountry={selectedCountry}
      />

      
      {COUNTRY_INFO[selectedCountry].is_in_development ? (
        <div id="poll-page-comingsoon">
          <p>Coming soon for selected country...</p>
        </div>
      ) : (
        <div id="poll-page-content">
          
          {selectedCountry === 'usa' ? (
            <VoteLongitudinalUSPollsters />
          ) : (
            <VoteLongitudinal />
          )}

          <VoteLongitudinalDemographics />
        </div>
      )}


      
    </div>
  );
}

export default PollPage;
