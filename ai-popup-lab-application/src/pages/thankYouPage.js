import './thankYouPage.css';
import gear from '../assets/svgs/gear.svg';

function ThankYouPage() {
  return (
    <div className="ThankYouPage unbounded-weight300">

      <img className="gear gear-top" src={gear} alt="" />

      <div className="thank-you-text">
        <h1>THANK YOU</h1>
        <h2>FOR SUPPORTING</h2>
        <h3>MECHANICAL POLLSTER</h3>
      </div>

      <img className="gear gear-bottom" src={gear} alt="" />

    </div>
  );
}

export default ThankYouPage;