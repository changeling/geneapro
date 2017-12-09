import * as React from 'react';
import * as d3Hierarchy from 'd3-hierarchy';
import * as d3Shape from 'd3-shape';
import { Link } from 'react-router-dom';
import { RadialSettings } from '../Store/Radial';
import { Person } from '../Store/Person';
import ScalableSVG from '../SVG.Scalable';
import { BasePersonLayout, Style, styleToString } from '../style';
import './Radial.css';

interface RadialLayout extends BasePersonLayout {
   p: Person;
   childNodes: RadialLayout[];
}

interface RadialProps {
   settings: RadialSettings;
   persons: {[id: number]: Person};
   decujus: number;
}

export default function Radial(props: RadialProps) {
   const circleSize = 5;  // diameter of circles
   const diameter = 2 * Math.abs(props.settings.generations) *
      props.settings.spacing;
   // We are displaying gens*2+1 generations, and leave space
   // between two circles equal to 9 times the size of a circle.

   function buildTree(pid: number|null,
                      generation: number,
                      sosa: number,
                      fromAngle: number,
                      toAngle: number) {
      if (pid === null ||
          !(pid in props.persons) ||
          generation > Math.abs(props.settings.generations)) {
         return null;
      }
      const p: Person = props.persons[pid];
      const relatives = (props.settings.generations > 0 ?
         p.parents : p.children) || [];
      const sosaStep = 1 / Math.max(relatives.length - 1, 1);
      const angleStep = (toAngle - fromAngle) / relatives.length;

      const result: RadialLayout = {
         p: p,
         generation: generation,
         sosa: sosa,
         angle: fromAngle,
         childNodes:
            relatives.map((parent, index) => buildTree(
               parent,
               generation + 1,
               sosa * 2 + index * sosaStep,
               fromAngle + index * angleStep,
               fromAngle + (index + 1) * angleStep))
            .filter(e => e !== null) as RadialLayout[]
      };
      return result;
   }

   const rootNode = buildTree(props.decujus, 0, 1, 0, 1);
   if (!rootNode) {
      return null;
   }

   const root = d3Hierarchy.hierarchy<RadialLayout>(
      rootNode,
      d => d.childNodes
   );

   const treeLayout = d3Hierarchy.tree<RadialLayout>()
      .nodeSize([circleSize, circleSize])
      .size([2 * Math.PI, diameter / 2])
      .separation((p1, p2) => (p1.parent === p2.parent ? 1 : 2) / p1.depth);

   const tree = treeLayout(root);
   const allNodes = tree.descendants();

   // Handling of duplicate persons in the tree: only one node is represented
   // but multiple links
   let coords: {[id: number]: d3Hierarchy.HierarchyPointNode<RadialLayout>} = {};
   allNodes.map(node => coords[node.data.p.id] = node);

   const circles = Object.values(coords).map(
      (node: d3Hierarchy.HierarchyPointNode<RadialLayout>) => (
         <Link
            to={node.data.p ? '/radial/' + node.data.p.id : '#'}
            key={node.data.p.id}
         >
            <g
               className="node"
               transform={`rotate(${node.x * 180 / Math.PI - 90})translate(${node.y})`}
            >
               <circle
                  r={circleSize}
                  key={node.data.p.id}
                  {...styleToString(Style.forPerson(props.settings.colors, node.data))}
               />
               {
                  <text
                     dy=".31em"
                     textAnchor={node.x < Math.PI ? 'start' : 'end'}
                     transform={node.x < Math.PI ? 'translate(8)' : 'rotate(180)translate(-8)'}
                  >
                     {
                        props.settings.showText ?
                           node.data.p.surn :
                           node.data.p.surn + ' ' + node.data.p.givn
                     }
                  </text>
               }
            </g>
         </Link>
      )
   );

   const radialLink = d3Shape.linkRadial<d3Hierarchy.HierarchyPointLink<RadialLayout>,
                                         d3Hierarchy.HierarchyPointNode<RadialLayout>>()
       .angle(d => coords[d.data.p.id].x)
       .radius(d => coords[d.data.p.id].y);

   const lines = tree.links().map(
      (link, index) => (
         <path
            className="link"
            key={index}
            d={radialLink(link) || ''}
         />
      )
   );

   const defs = null;

   return (
      <ScalableSVG className={'Radial ' + (props.settings.showText ? 'visibleNames' : '')}>
         <defs>
            {defs}
         </defs>
         <g transform={`translate(${diameter / 2 + 20},${diameter / 2 + 20})`}>
            {lines}
            {circles}
         </g>
      </ScalableSVG>
   );
}