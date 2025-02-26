import os

from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_autoscaling as autoscaling,
    aws_iam as iam,
    CfnOutput,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets
)
from constructs import Construct

class CopilotApiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(self, "FlaskStackVPC",
                    max_azs=2,
                    subnet_configuration=[
                        ec2.SubnetConfiguration(
                            name="Private",
                            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                            cidr_mask=24
                        ),
                        ec2.SubnetConfiguration(
                            name="Public",
                            subnet_type=ec2.SubnetType.PUBLIC,
                            cidr_mask=24
                        )
                    ]
                    )

        # Create a security group for the EC2 instances
        security_group = ec2.SecurityGroup(self, "EC2SecurityGroup",
                                           vpc=vpc,
                                           allow_all_outbound=True,
                                           description="Security group for EC2 instances"
                                           )

        # Create a launch template
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "apt-get update",
            # Install SSM agent
            "sudo snap install amazon-ssm-agent --classic",
            "sudo systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service",
            "sudo systemctl start snap.amazon-ssm-agent.amazon-ssm-agent.service",
            # Install AWS CLI v2
            "apt install unzip",
            'curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"',
            "unzip awscliv2.zip",
            "sudo ./aws/install",
            # add any additional commands that you'd like to run on instance launch here
        )

        # Look up the latest Ubuntu 24.04 ARM64 AMI
        ubuntu_arm_ami = ec2.MachineImage.lookup(
            name="ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-arm64-server-*",
            owners=["099720109477"],  # Canonical's AWS account ID
            filters={"architecture": ["arm64"]}
        )

        ec2_role_name = "Proj-Flask-LLM-ALB-EC2-Role"
        ec2_role = iam.Role(self, "EC2Role",
                            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                            managed_policies=[
                                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
                                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchAgentServerPolicy"),
                                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchLogsFullAccess"),
                                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess")
                            ],
                            role_name=ec2_role_name,
                            )

        launch_template = ec2.LaunchTemplate(self, "LaunchTemplate",
                                             instance_type=ec2.InstanceType("c8g.xlarge"),
                                             machine_image=ubuntu_arm_ami,
                                             user_data=user_data,
                                             security_group=security_group,
                                             role=ec2_role,
                                             detailed_monitoring=True,
                                             block_devices=[
                                                 ec2.BlockDevice(
                                                     device_name="/dev/sda1",
                                                     volume=ec2.BlockDeviceVolume.ebs(
                                                         volume_size=50,
                                                         volume_type=ec2.EbsDeviceVolumeType.GP3,
                                                         delete_on_termination=True
                                                     )
                                                 )
                                             ]
                                             )

        # Create an Auto Scaling Group
        asg = autoscaling.AutoScalingGroup(self, "ASG",
                                           vpc=vpc,
                                           vpc_subnets=ec2.SubnetSelection(
                                               subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                                           launch_template=launch_template,
                                           min_capacity=1,
                                           max_capacity=1,
                                           desired_capacity=1
                                           )

        # Create an Application Load Balancer
        alb = elbv2.ApplicationLoadBalancer(self, "ALB",
                                        vpc=vpc,
                                        internet_facing=True,
                                        vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
                                        )
        

        # Generate a certificate for the ALB's default domain
        certificate = acm.Certificate.from_certificate_arn(
            self,
            "Certificate",
            os.environ["ACM_CERTIFICATE_ARN"]
        )

        # Add a listener to the ALB with HTTPS
        listener = alb.add_listener("HttpsListener",
                                    port=443,
                                    certificates=[certificate],
                                    ssl_policy=elbv2.SslPolicy.RECOMMENDED)

        # Add the ASG as a target to the ALB listener
        listener.add_targets("ASGTarget",
                             port=8080,
                             targets=[asg],
                             protocol=elbv2.ApplicationProtocol.HTTP,
                             health_check=elbv2.HealthCheck(
                                 path="/health",
                                 healthy_http_codes="200-299"
                             ))

        hosted_zone = route53.HostedZone.from_lookup(self, "HostedZone",
                                                     domain_name=os.environ["HOSTED_ZONE_DOMAIN_NAME"],
                                                     )

        # Create an A record for the subdomain
        route53.ARecord(self, "ALBDnsRecord",
                        zone=hosted_zone,
                        record_name=os.environ["SUBDOMAIN_NAME"],
                        target=route53.RecordTarget.from_alias(targets.LoadBalancerTarget(alb))
                        )

        # Output the ALB DNS name and database endpoint
        CfnOutput(self, "LoadBalancerDNS",
                  value=alb.load_balancer_dns_name,
                  description="The DNS name of the Application Load Balancer")
        
        CfnOutput(self, "DatabaseEndpoint",
                  value=db_instance.instance_endpoint.hostname,
                  description="The endpoint of the RDS database")