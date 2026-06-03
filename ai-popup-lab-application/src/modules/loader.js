// CSS based which shows three dots with a loading esque animation, used often when data for components has not loaded from backend

import './loader.css';

function Loader() {

  return (
    <div className="Loader">
      <div></div>
      <div></div>
      <div></div>
    </div>
  );
};

export default Loader;