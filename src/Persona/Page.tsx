import * as React from 'react';
import { connect } from 'react-redux';
import { RouteComponentProps } from 'react-router';
import { Loader } from 'semantic-ui-react';
import { PersonSet, personDisplay } from '../Store/Person';
import { addToHistory } from '../Store/History';
import { AppState, GPDispatch } from '../Store/State';
import { fetchPersonDetails } from '../Store/Sagas';
import Page from '../Page';
import Persona from '../Persona/Persona';

interface PropsFromRoute {
   id: string;
}

interface PersonaPageProps extends RouteComponentProps<PropsFromRoute> {
   id: number;
   persons: PersonSet;
   dispatch: GPDispatch;
}

class PersonaPageConnected extends React.PureComponent<PersonaPageProps> {
   componentDidMount() {
      this.calculateData();
   }

   componentDidUpdate(old: PersonaPageProps) {
      if (old.id !== this.props.id) {
         this.calculateData();
      }

      const p = this.props.persons[this.props.id];
      this.props.dispatch(addToHistory({person: p}));
   }

   calculateData() {
      this.props.dispatch(fetchPersonDetails.request({id: this.props.id}));
   }

   render() {
      const p = this.props.persons[this.props.id];
      document.title = p ? personDisplay(p) : 'Persona';
      return (
         <Page
            decujus={p}
            main={p ?
               <Persona
                  person={p}
               /> :
               <Loader active={true} size="large">Loading</Loader>
            }
         />
      );
   }
}

const PersonaPage = connect(
   (state: AppState, props: RouteComponentProps<PropsFromRoute>) => ({
      ...props,
      persons: state.persons,
      id: Number(props.match.params.id),
   }),
   (dispatch: GPDispatch) => ({
      dispatch,
   }),
)(PersonaPageConnected);

export default PersonaPage;
