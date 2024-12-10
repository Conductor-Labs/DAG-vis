# app.py

import streamlit as st
import json
import logging
from io import BytesIO
from streamlit_flow import streamlit_flow
from streamlit_flow.elements import StreamlitFlowNode, StreamlitFlowEdge
from streamlit_flow.state import StreamlitFlowState
from streamlit_flow.layouts import LayeredLayout

st.set_page_config(
    page_title="Conductor Process Flow Visualizer",
    page_icon="💡",
    layout="wide",
)

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a simple logging decorator
def with_logging(func):
    def wrapper(*args, **kwargs):
        logger.info(f"Starting '{func.__name__}'")
        result = func(*args, **kwargs)
        logger.info(f"Finished '{func.__name__}'")
        return result
    return wrapper

@with_logging
def main():
    st.title("DAG Visualization & Editing")
    st.write("Upload and visualize a DAG JSON file. Interactively add, edit, or delete nodes and edges.")

    # Function to load DAG from uploaded file
    def load_dag(uploaded_file):
        try:
            data = json.load(uploaded_file)
            st.success("DAG JSON uploaded successfully.")
            return data
        except Exception as e:
            st.error(f"Error reading JSON file: {e}")
            return None

    # File uploader
    uploaded_file = st.file_uploader("Upload DAG JSON file", type=["json"])

    if uploaded_file is not None:
        # Load the DAG
        dag_data = load_dag(uploaded_file)

        if dag_data:
            # Extract nodes and edges
            nodes_data = dag_data.get('unit_operations', {})
            edges_data = dag_data.get('streams', {})

            # Collect node IDs for validation
            node_ids = set()
            for node in nodes_data.values():
                node_id = node.get('unit_operation_id', '')
                if node_id:
                    node_ids.add(node_id)

            # Map nodes to StreamlitFlowNodes
            nodes = []
            for node in nodes_data.values():
                node_id = node.get('unit_operation_id', '')
                node_name = node.get('name', '')
                if not node_id:
                    continue  # Skip nodes without an ID

                # Determine node type
                node_type = 'default'
                # If no incoming edges, consider it an "input" node
                if not any(edge['target'] == node_id for edge in edges_data.values()):
                    node_type = 'input'
                # If no outgoing edges, consider it an "output" node
                if not any(edge['source'] == node_id for edge in edges_data.values()):
                    node_type = 'output'

                # Set positions (will be laid out automatically)
                source_position = 'right'
                target_position = 'left'

                # Put full node info into node.data so we can retrieve it later
                node_data_dict = {
                    'content': node_name,
                    'description': node.get('description', ''),
                    'unit_operation_type': node.get('unit_operation_type', ''),
                    'order': node.get('order', None),
                    'input_streams': node.get('input_streams', []),
                    'output_streams': node.get('output_streams', []),
                    'parameters': node.get('parameters', {}),
                    'additional_info': node.get('additional_info', '')
                }

                st_node = StreamlitFlowNode(
                    id=node_id,
                    pos=(0, 0),  # Positions will be auto-laid out anyway
                    data=node_data_dict,
                    node_type=node_type,
                    source_position=source_position,
                    target_position=target_position,
                    deletable=True
                )
                nodes.append(st_node)

            # Map edges to StreamlitFlowEdges
            edges = []
            for edge in edges_data.values():
                stream_id = edge.get('stream_id', '')
                source = edge.get('source', '')
                target = edge.get('target', '')
                edge_name = edge.get('name', '')
                stream_type = edge.get('stream_type', '')
                animated = True if stream_type == 'core' else False

                if source not in node_ids or target not in node_ids:
                    st.warning(f"Edge {stream_id} refers to unknown node(s): source={source}, target={target}")
                    continue

                st_edge = StreamlitFlowEdge(
                    id=stream_id,
                    source=source,
                    target=target,
                    label=edge_name,
                    animated=animated,
                    deletable=True
                )
                edges.append(st_edge)

            # Initialize state
            initial_state = StreamlitFlowState(nodes=nodes, edges=edges)

            st.markdown("### Interactively edit the DAG below")

            # Make the flow fully interactive
            new_state = streamlit_flow(
                'fully_interactive_dag',
                initial_state,
                fit_view=True,
                show_controls=True,
                allow_new_edges=True,
                animate_new_edges=True,
                layout=LayeredLayout(direction='right'),
                enable_pane_menu=True,
                enable_edge_menu=True,
                enable_node_menu=True,
            )

            # Display updated metrics
            col1, col2 = st.columns(2)
            col1.metric("Nodes", len(new_state.nodes))
            col2.metric("Edges", len(new_state.edges))

            # If a node is selected, allow editing its fields
            selected_node_id = new_state.selected_id
            if selected_node_id:
                # Find the node
                selected_node = None
                for n in new_state.nodes:
                    if n.id == selected_node_id:
                        selected_node = n
                        break

                if selected_node:
                    with st.sidebar:
                        st.markdown("### Edit Selected Node")
                        node_content = selected_node.data.get('content', '')
                        node_description = selected_node.data.get('description', '')
                        node_type = selected_node.data.get('unit_operation_type', '')
                        node_order = selected_node.data.get('order', 0)
                        node_input_streams = selected_node.data.get('input_streams', [])
                        node_output_streams = selected_node.data.get('output_streams', [])
                        node_parameters = selected_node.data.get('parameters', {})
                        node_additional_info = selected_node.data.get('additional_info', '')

                        with st.form(key="node_edit_form"):
                            new_name = st.text_input("Name", node_content)
                            new_description = st.text_area("Description", node_description)
                            new_unit_type = st.text_input("Unit Operation Type", node_type)
                            new_order = st.number_input("Order", value=node_order)
                            new_input_streams_str = st.text_area("Input Streams (comma-separated)", ",".join(node_input_streams))
                            new_output_streams_str = st.text_area("Output Streams (comma-separated)", ",".join(node_output_streams))

                            st.markdown("#### Parameters")
                            # Simple way to edit parameters: show a text area with JSON
                            parameters_str = st.text_area("Parameters (JSON)", json.dumps(node_parameters, indent=2))

                            new_additional_info = st.text_area("Additional Info", node_additional_info)

                            if st.form_submit_button("Update Node"):
                                # Update the node's data
                                selected_node.data['content'] = new_name
                                selected_node.data['description'] = new_description
                                selected_node.data['unit_operation_type'] = new_unit_type
                                selected_node.data['order'] = new_order
                                selected_node.data['input_streams'] = [s.strip() for s in new_input_streams_str.split(',') if s.strip()]
                                selected_node.data['output_streams'] = [s.strip() for s in new_output_streams_str.split(',') if s.strip()]

                                # Parse parameters JSON
                                try:
                                    updated_params = json.loads(parameters_str)
                                except json.JSONDecodeError:
                                    st.error("Invalid JSON for parameters. Reverting to old parameters.")
                                    updated_params = node_parameters
                                selected_node.data['parameters'] = updated_params
                                selected_node.data['additional_info'] = new_additional_info

                                # Trigger a rerun to show updated changes in the DAG
                                st.experimental_rerun()

            # Prepare updated DAG for download
            updated_dag = {
                "unit_operations": {},
                "streams": {}
            }

            # Process updated nodes
            for node in new_state.nodes:
                # Ensure position exists and has 'x' and 'y'
                position = node.position if hasattr(node, 'position') else {'x': 0, 'y': 0}
                updated_dag["unit_operations"][node.id] = {
                    "unit_operation_id": node.id,
                    "name": node.data.get('content', ''),
                    "description": node.data.get('description', ''),
                    "unit_operation_type": node.data.get('unit_operation_type', ''),
                    "order": node.data.get('order', 0),
                    "input_streams": node.data.get('input_streams', []),
                    "output_streams": node.data.get('output_streams', []),
                    "parameters": node.data.get('parameters', {}),
                    "additional_info": node.data.get('additional_info', ''),
                    "position": {
                        "x": int(position.get('x', 0)),
                        "y": int(position.get('y', 0))
                    }
                }

            # Process updated edges
            for edge in new_state.edges:
                updated_dag["streams"][edge.id] = {
                    "stream_id": edge.id,
                    "source": edge.source,
                    "target": edge.target,
                    "name": edge.label,
                    "stream_type": "core" if edge.animated else "other"
                }

            # Display updated DAG
            st.write("### Updated state of the DAG:")
            st.json(updated_dag)

            # Prepare download content
            updated_dag_json = json.dumps(updated_dag, indent=2)
            st.download_button(
                label="Download Updated DAG JSON",
                data=updated_dag_json,
                file_name="updated_dag.json",
                mime="application/json"
            )
    else:
        st.info("Please upload a DAG JSON file to get started.")

if __name__ == "__main__":
    main()
